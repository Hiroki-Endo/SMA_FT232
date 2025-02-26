# Created by Askar based on a gitbuh project
# Modified in 2022 10 14
from ast import Pass
import math, time, sys
from lib.GENERALFUNCTIONS import *

class Pca9685_01(object):
  # Registers/etc.
  __MODE1              = 0x00
  __MODE2              = 0x01

  __SUBADR1            = 0x02
  __SUBADR2            = 0x03
  __SUBADR3            = 0x04
  
  # __SWRST              = 0x06
  
  
  __PRESCALE           = 0xFE

  __LED0_ON_L          = 0x06
  __LED0_ON_H          = 0x07
  __LED0_OFF_L         = 0x08
  __LED0_OFF_H         = 0x09
  
  __LED15_ON_L          = 0x42
  
  __ALLLED_ON_L        = 0xFA
  __ALLLED_ON_H        = 0xFB
  __ALLLED_OFF_L       = 0xFC
  __ALLLED_OFF_H       = 0xFD
  
  def __init__(self, i2c_controller,address=0x40,easy_mdoe= True,debug=False,):
    print("Creating New PCA9685 IIC slave :",hex(address))
    
    self.i2c_controller = i2c_controller
    # self.FT232_chip = i2c_controller.ftdi()
    
    # Get a port to an I2C slave device
    self.slave = i2c_controller.get_port( address ) # 0x21 
    # self.slave = smbus.SMBus(1)

    self.address = address
    self.debug = debug
    self.osc_clock = 25000000.0
    self.easy_mdoe = easy_mdoe 
    self.OCH_mode = False
    self.setOCH()
    self.reset()


  def reset(self): #BUG
    i2c_controller = self.i2c_controller
    #     The SWRST Call function is defined as the following:
    # 1. A START command is sent by the I2C-bus master.
    i2c_controller._do_prolog( (self.address << 1) & i2c_controller.HIGH )
    # 2. The reserved SWRST I2C-bus address ‘0000 0000’ with the R/W bit set to ‘0’ (write) is
    # sent by the I2C-bus master.

    # 3. The PCA9685 device(s) acknowledge(s) after seeing the General Call address
    # ‘0000 0000’ (00h) only. If the R/W bit is set to ‘1’ (read), no acknowledge is returned to
    # the I2C-bus master.

    self.write(0x00,bytearray([0x06]),doCheck=False)

    # 4. Once the General Call address has been sent and acknowledged, the master sends
    # 1 byte with 1 specific value (SWRST data byte 1):
    # a. Byte 1 = 06h: the PCA9685 acknowledges this value only. If byte 1 is not equal to
    # 06h, the PCA9685 does not acknowledge it.
    # If more than 1 byte of data is sent, the PCA9685 does not acknowledge any more.

    # 5. Once the correct byte (SWRST data byte 1) has been sent and correctly
    # acknowledged, the master sends a STOP command to end the SWRST Call: the
    # PCA9685 then resets to the default value (power-up value) and is ready to be
    # addressed again within the specified bus free time (tBUF).
    
    
    
    # print(self.read(__SWRST))

    print('\nSucess Reseted PCA9685 board:0x%02X'%self.address)
    self.i2c_controller._do_epilog()

    if (self.debug): 
      print("Reseting PCA9685: ",'%#x'%self.address )
      print("Initial Mode_1 reg value: ",'%#x'%self.read(self.__MODE1))
      print("Initial Mode_2 reg value: ",'%#x'%self.read(self.__MODE2))

    return []

  def restart(self):
    print('\n Restart PCA9685 board:0x%02X\n\tThe PWM in regs will be runned from the start'%self.address)
    # 1. Read MODE1 register.
    mode1_data = self.read(self.__MODE1)      
    print("\t0x%02X.Mode1_data:0x%02X"%(self.address,mode1_data))

    # 2. Check that bit 7 (RESTART) is a logic 1. If it is, clear bit 4 (SLEEP). 
        # Allow time for oscillator to stabilize (500 us).
    if (mode1_data >>6)==1: 
      mode1_data = self.write(self.__MODE1,mode1_data & 0xEF) # 239=1110 1111

    # 3. Write logic 1 to bit 7 of MODE1 register. All PWM channels will restart and the
    # RESTART bit will clear
    self.slave.write_to( regaddr= self.__MODE1, out=bytearray(mode1_data | 128 ))


    pass

  def quickShutdown(self):
    "Two methods can be used to do an orderly shutdown." 
    "Fastest: write logic 1 to bit 4 in register ALL_LED_OFF_H. "
    self.slave.write_to( regaddr= self.__ALLLED_OFF_H, out= bytearray([0x11]) )
    "Method2: write logic 1 to bit 4 in each active PWM channel LEDn_OFF_H register. "
    pass

  def testPort(self,port): # Add by askar @ 20220703
    print('\n---Testing port: ',hex(port), ' In mode: ', hex(self.read(self.__MODE1)))
    
    old_value = self.read(port)
    test_value = old_value + 1
    
    self.write(port, test_value)
    changed_value = self.read(port)
    
    self.write(port, old_value)  
    final_value = self.read(port)

    print("Ori value: ",old_value,'/',hex(old_value),' Input: ',test_value,'/',hex(test_value),
        '\nChanged content: ',changed_value,'Final content: ',final_value)
    pass

  def testChannle(self,channel_num):

    if (channel_num<0) or channel_num >15: 
      print("\nIllegal PWM channel: ",channel_num,"\n\tChannel number should in range: [0,15]")
      return False
    else:  
      port = self.__LED0_ON_L + (channel_num)*4
      if self.debug: print('\nTesting channel: ',channel_num,'; Port: ',port,'/',hex(port))

    # self.sleep(True)
    # self.write(self.__MODE1, 0x11)
   
    self.write(port, 0x99) # ON L
    self.write(port+1, 0x01) # ON H
    self.write(port+2, 0xCC) # LOW L
    self.write(port+3, 0x04) # LOW H
    
    self.write(self.__MODE1, 0x01)
    # time.pause(0.5)
    self.setDutyRatioCH(channel_num,0)

    pass

  def write(self, reg_add, input_value, doCheck = True):
    "Writes an 8-bit value to the specified register/address"
    
    if doCheck :value_before =  (self.slave.read_from(regaddr=reg_add, readlen=1))[0]#

    if isinstance(input_value,int): in_value =  bytearray([input_value]) 
    else: in_value = input_value

    self.slave.write_to( regaddr= reg_add, out= in_value)
    
    if doCheck: # Check
      time.sleep(0.1)
      value_after =  self.slave.read_from(regaddr=reg_add, readlen=1)[0]# self.read(reg_add)
      if (value_after-value_before) == 0:
        if input_value == value_after: 
          if self.debug: print("\tInputted and saved values are equal, however it is still writted!")
        else: 
          print("\tValue is changed, however does not mattches the desire value!")
          print("\tConsider chaecking the chip datasheet about the correct value for changing")
          
      # if self.debug: print("\tI2C: Device 0x%02X writted 0x%02X to reg 0x%02X" % (self.address, input_value, reg_add))
      return value_after
    return in_value
    
  def read(self, reg): 
    "Read an unsigned byte from the I2C device"
    # result = self.slave.read_byte_data(self.address, reg)
    result = (self.slave.read_from(regaddr = reg,readlen=1))[0]
    # result
    if self.debug: print("\tI2C: Device 0x%02X returned 0x%02X from reg 0x%02X" % (self.address, result & 0xFF, reg))
    return result

  def setPWMFreq(self, freq):
    "Sets the PWM frequency"
    prescale_val =     self.osc_clock/4096    # 25MHz 12-bit
    prescale_val = round(prescale_val/float(freq) )-1

    # if (self.debug):
    print("Setting PWM frequency to %d Hz" % freq)
    print("Estimated pre-scale: %d" % prescale_val)
    
    prescale = prescale_val # math.floor(prescaleval + 0.5)
    
    if (self.debug):      print("Final pre-scale: %d" % prescale)

    oldmode = self.read(self.__MODE1)
    newmode = (oldmode & 0x7F) | 0x10        # sleep
    # print("\tOld mode:0x%02X"%oldmode, " Mode to write:0x%02X"%newmode)

    self.slave.write_to( regaddr=self.__MODE1, out=bytearray([newmode])) # go to sleep
    print("\tWritting value: ",prescale,", to prescale reg ",hex(self.__PRESCALE))
    self.slave.write_to( regaddr=self.__PRESCALE, out=bytearray([prescale]) ) # Value
    print("\tBack to awake mode")
    self.slave.write_to( regaddr=self.__MODE1, out=bytearray([oldmode])) # Restart sign
    
  def setOCH(self):
    self.OCH_mode = True

    oldmode1 = self.read(self.__MODE1)
    newmode1 = (oldmode1 & 0x7F) | 0x10        # sleep
    # print("\tOld mode:0x%02X"%oldmode, " Mode to write:0x%02X"%newmode)

    self.slave.write_to( regaddr=self.__MODE1, out=bytearray([newmode1])) # go to sleep

    oldmode2 = self.read(self.__MODE2)
    newmode2 = (oldmode2 | 0x08) # OCH ON/OFF

    # print("\tWritting value: ",prescale,", to prescale reg ",hex(self.__PRESCALE))
    self.slave.write_to( regaddr=self.__MODE2, out=bytearray([newmode2]) ) # Value

    print("\tBack to awake mode")
    self.slave.write_to( regaddr=self.__MODE1, out=bytearray([oldmode1])) # Restart sign
    print("oldmode2: 0x%02X New:0x%02X" % (oldmode2, self.read(self.__MODE2)) )

  def getPWMFreq(self):
    cur_prescala = self.read(self.__PRESCALE)
    cur_freq = self.osc_clock/((cur_prescala+1)*4096)
    return cur_freq

  def setPWM(self, channel, on, off):
    "Sets a single PWM channel"
    print(" IN/out: ", self.__LED0_ON_L+4*channel, self.read(self.__LED0_ON_L+4*channel))
    
    print("On: ",on,',',on & 0xFF,' ',on >> 8,'; Off', off)

    self.write(self.__LED0_ON_L+4*channel, on & 0xFF) # & 1111 1111
    self.write(self.__LED0_ON_H+4*channel, on >> 8)
    self.write(self.__LED0_OFF_L+4*channel, off & 0xFF)
    self.write(self.__LED0_OFF_H+4*channel, off >> 8)
    
    if (self.debug):      print("\tChannel: %d  LED_ON: %d LED_OFF: %d" % (channel,on,off))

  def setDutyRatioCH(self,channel,duty_ratio,stop_sending=True):

    if not self.easy_mdoe:
      print("Pls use easy mode to Duty Ratio!"); return []
    if (channel<0) or channel >15: 
      print("\nIllegal PWM channel: ",channel,"\n\tShould in range: [0,15]"); return []
    elif duty_ratio<0 or duty_ratio>1:
      print("\n\n\t\t Illegeal DUTY RATIO!! \nPlease set duty ratio to 0-1"); return []

    else:  
      port = self.__LED0_ON_L + (channel)*4
      # if self.debug: print('\nTesting channel: ',channel,'; Port: ',channel,'/',hex(channel))
      
      off_time =int((4096-1) * duty_ratio )# [off_time_H,off_time_L] = [0000,off_time(12Bit)]
      
      off_time_L = off_time & 0xFF
      off_time_H = off_time >> 8
      
      if stop_sending and (not self.OCH_mode):
        self.slave.write_to( regaddr=port, out=bytearray([0x00]),relax=False ) # Value
        self.slave.write_to( regaddr=port+1, out=bytearray([0x00]),relax=False ) # Value
        self.slave.write_to( regaddr=port+2, out=bytearray([off_time_L]),relax=False ) # Value
        self.slave.write_to( regaddr=port+3, out=bytearray([off_time_H])) # Value
        print("S2")
      else:
        self.slave.write_to( regaddr=port, out=bytearray([0x00]),relax=False ) # Value
        self.slave.write_to( regaddr=port+1, out=bytearray([0x00]),relax=False ) # Value
        self.slave.write_to( regaddr=port+2, out=bytearray([off_time_L]),relax=False ) # Value
        self.slave.write_to( regaddr=port+3, out=bytearray([off_time_H]),relax=False) # Value
    return []

  def setDutyRatioCHS(self,channels,duty_ratio,stop_sending=False): # 20220815
    if len(channels) >= 1:
      for _ch in channels[:len(channels)-1]: 
        self.setDutyRatioCH(_ch,duty_ratio,stop_sending=False)
    else :print("\nNo target channel!"); return []
    self.setDutyRatioCH(channels[-1],duty_ratio,stop_sending)   

    return []

  def setServoPulse(self, channel, pulse):
    "Sets the Servo Pulse,The PWM frequency must be 50HZ"
    freq = 50 #Hz
    period = 1000000 / freq # period (us)
    pulse = int(pulse*4096/20000)        #PWM frequency is 50HZ,the period is 20000us

    print('pulse: ',pulse)
     
    self.setPWM(channel, 0, pulse)
  
  # 手部功能的初级实现！ 后需另外建立lib
  def test_wires(self,channels,dutys,intervals,conf0 = False):
    # [active_duty,sustain_duty,stop_duty] = dutys
    # [burst_interval,sustain_interval,stop_interval] = intervals
    # if not len(dutys)==len(intervals): 
    #   print("\n\nError!\tin test_wires\t"); return []

    # if conf0 and not channels[-1]==0 : channels.append(0)

    for _duty,_interval in zip(dutys,intervals) :
        print("PCA Setting Duty Ratio",channels,_duty,_interval)
        self.setDutyRatioCHS(channels,_duty)
        print("DR SET at:", time.time()- RUNTIME," Related to ",time.strftime('%Y:%m:%d %H:%M:%S', time.localtime(RUNTIME)) )

        time.sleep(_interval)
        self.setDutyRatioCHS(channels,0)
        print("DR OVER at:", time.time()- RUNTIME," Related to ",time.strftime('%Y:%m:%d %H:%M:%S', time.localtime(RUNTIME)) )


