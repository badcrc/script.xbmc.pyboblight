# -*- coding: utf-8 -*- 
'''
    Boblight for Kodi
    Copyright (C) 2012, 2020 Team XBMC, bobo1on1, Memphiz, wrtlprnft

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.
    
    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''


import socket
import time
from resources.lib.tools import *



class Light(object):
    """Represents a single light"""
    
    def __init__(self,name,client):
        self.client=client
        self.name=name
        self.hmin=0.0
        self.hmax=100.0
        self.vmin=0.0
        self.vmax=100.0
        
        self.r=0
        self.g=0
        self.b=0
        

    def set_color(self,r,g,b):
        self.r=r
        self.g=g
        self.b=b
        
    def __str__(self):
        return """<Light name='%s' hscan='%s-%s' vscan='%s-%s' color='%s/%s/%s'>"""%(self.name,self.hmin,self.hmax,self.vmin,self.vmax,self.r,self.g,self.b)
    
    
    def __repr__(self):
        return str(self)
    

class Boblight():
  def __init__( self, *args, **kwargs ):
    self.current_priority = -1
    self.libboblight      = None
    self.bobHandle        = None
    self.connected        = False
    self.hostip           = '127.0.0.1'
    self.hostport         = 19333
    self.sock             = None
    self.socketerror      = False
    self.lights           = {}
    self.width            = 0
    self.height           = 0



  def _send_command(self,command):
    if not self.connected:
        self.bob_connect(self.hostip, self.hostport)
    try:
        self.sock.sendall(str.encode(command))
        self.sock.sendall(b'\r\n')
    except Exception as e:
        #log(e)
        self.socketerror=True

  def _readline(self):
    try:
        msg=self.sock.recv(1024).decode().strip()
        return msg
    except:
        self.socketerror=True
        return None
  
  def _sync(self):
    if self.lastupdate > time.time()-0.1:
        return
    else:
        self.lastupdate=time.time()
    self._send_command('sync')

  def _refresh_lights_info(self):
    self._send_command("get lights")
    recv=self._readline()
    ans=recv.split()
    lights=recv.split('\n')
    #assert len(ans)==2
    assert ans[0]=='lights',"Expected 'lights <num>' but got '%s'"%ans
    nlights=int(ans[1])

    tempdic={}
    for i in range(nlights):
        linfo=lights[i+1].split()
        assert len(linfo)==7
        assert linfo[0]=='light'
        assert linfo[2]=='scan'
        kw1,name,kw2,vmin,vmax,hmin,hmax=linfo
        l=Light(name, self)
        l.hmin=float(hmin)
        l.hmax=float(hmax)
        l.vmin=float(vmin)
        l.vmax=float(vmax)
        tempdic[name]=l
    self.lights=tempdic 

  def _prepare_rgb_color(self,lightname,r,g,b):
    fr=round(r/255.0,6)
    fg=round(g/255.0,6)
    fb=round(b/255.0,6)
    self._send_command("set light %s rgb %s %s %s"%(lightname,fr,fg,fb))

  def _update(self):
    for k,light in self.lights.items():
      self._prepare_rgb_color(light.name, light.r, light.g, light.b)
    self._sync()

  def _handshake(self):
    self._send_command('hello')
    ret=self._readline()
    if ret!='hello':
        raise Exception("hello failed")
    self._send_command("set priority %s"%self.current_priority)
    
    #refresh server info
    if self.lights=={}:
      self._refresh_lights_info()

  
  def bob_set_priority(self,priority):   
    ret = True
    if self.connected:
      if priority != self.current_priority:
        self.current_priority = priority
        self._send_command("set priority %s"%self.current_priority)
        #if not self.libboblight.boblight_setpriority(self.bobHandle, self.current_priority):
    return ret
    
  def bob_setscanrange(self,width, height):
    #if self.connected:
    self.width = width
    self.height = height
    #self.libboblight.boblight_setscanrange(self.bobHandle, width, height)
    
  def bob_addpixelxy(self,x,y,rgb):
    if self.connected:
      #self.libboblight.boblight_addpixelxy(self.bobHandle, x, y, rgb)
      for k,light in self.lights.items():
        range_x_min=float((light.hmin * (self.width -1)) / 100.0)
        range_x_max=float((light.hmax * (self.width -1)) / 100.0)
        range_y_min=float((light.vmin * (self.height -1)) / 100.0)
        range_y_max=float((light.vmax * (self.height -1)) / 100.0)
        if range_x_min <= x <= range_x_max and range_y_min <= y <= range_y_max:
          #light.set_color(int(rgb[0]),int(rgb[1]),int(rgb[2]))
          self._prepare_rgb_color(light.name,int(rgb[0]),int(rgb[1]),int(rgb[2]))
      
  
  def bob_addpixel(self,rgb):
    if self.connected:
      self.libboblight.boblight_addpixel(self.bobHandle, -1, rgb)
  
  def bob_sendrgb(self):
    ret = False
    if self.connected:
      #ret = c_int(self.libboblight.boblight_sendrgb(self.bobHandle, 1, None))  != 0
      #for k,light in self.lights.items():
      #  self._prepare_rgb_color(light.name, light.r, light.g, light.b)
      self._sync()
      ret = True
    return ret
    
  def bob_setoption(self,option):
    ret = False
    if self.connected:
      opt = option.split('    ')
      if opt[0] == 'speed' or opt[0] == 'interpolation':
        if self.lights=={}:
          self._refresh_lights_info()
        for k,light in self.lights.items():
          self._send_command("set light %s %s"%(light.name,option)) #check if this works
        ret = True
      #ret = c_int(self.libboblight.boblight_setoption(self.bobHandle, -1, option.encode('latin-1')))  != 0
    else:
      ret = True
    return ret


    
  def bob_getnrlights(self):
    ret = 0
    if self.connected:
      #ret = c_int(self.libboblight.boblight_getnrlights(self.bobHandle))
      if self.lights=={}:
        self._refresh_lights_info()
      ret=len(self.lights)
    return ret

  def bob_getlightname(self,nr):
    ret = ""
    if self.connected:
      #ret = self.libboblight.boblight_getlightname(self.bobHandle,nr)
      if self.lights=={}:
        self._refresh_lights_info()
      i=0
      for k,light in self.lights.items():
        if i==nr:
          ret=light.name
          break
        else:
          i+=1
    return ret
  
  def bob_connect(self,hostip, hostport):    
    ret = False
    if hostip == None:
      self.hostip = '127.0.0.1'
    else:
      self.hostip = hostip
    if hostport == -1:
      self.hostport = 19333
    else:
      self.hostport = hostport
    try:
      ret = socket.create_connection((self.hostip, self.hostport))
      self.connected = 1
      self.sock = ret
      ret = True
    except socket.error:
      self.connected = 0

    if ret == True:
      self._handshake()
    return ret
    
  def bob_set_static_color(self,rgb):
    res = False
    if self.connected:
      if self.lights == {}:
        self._refresh_lights_info()
      for k,light in self.lights.items():
        light.set_color(int(rgb[0]),int(rgb[1]),int(rgb[2]))
      self._update()
      res = True
    return res  
  
  def bob_destroy(self):
    #self.libboblight.boblight_destroy(self.bobHandle)
    self._send_command('quit')
    self.sock.close()
    self.boblightLoaded = False
  
  def bob_geterror(self):
    ret = ""
    #ret = c_char_p(self.libboblight.boblight_geterror(self.bobHandle)).value
    ret=self._readline()
    return ret
  
  def bob_ping(self):
    ret = False
    if self.connected:
      #ret = c_int(self.libboblight.boblight_ping(self.bobHandle, None)).value == 1
      self._send_command("ping")
      recv=self._readline()
      ans=recv.split()
      if ans[0] == 'ping':
        ret = True
    return ret
