import socket,asyncore
import threading
from parse import parse

#thanks to agrynchuk for providing the code this is based on: https://stackoverflow.com/questions/12799348/how-to-make-a-dynamic-port-forwarding-on-python

class forwarder(asyncore.dispatcher):
	def __init__(self, ip, port, remoteip,remoteport,backlog=5):
		asyncore.dispatcher.__init__(self)
		self.lock=threading.Lock()
		self.remoteip=remoteip
		self.remoteport=remoteport
		self.create_socket(socket.AF_INET,socket.SOCK_STREAM)
		self.set_reuse_addr()
		self.bind((ip,port))
		self.listen(backlog)
	def updateRemote(self,remoteip,remoteport=6600):
		with self.lock:
			self.remoteip=remoteip
			self.remoteport=remoteport
	def getRemoteHost(self):
		with self.lock:
			return self.remoteip
	def getRemotePort(self):
		with self.lock:
			return self.remoteport
	def handle_accept(self):
		conn, addr = self.accept()
		# print '--- Connect --- '
		with self.lock:
			remoteip=self.remoteip
			remoteport=self.remoteport
		sender(receiver(conn),remoteip,remoteport)
	def closef(self):
		self.close()

class hostSelector(asyncore.dispatcher):
	def __init__(self, ip, port, forwarder,backlog=5):
		asyncore.dispatcher.__init__(self)
		self.create_socket(socket.AF_INET,socket.SOCK_STREAM)
		self.set_reuse_addr()
		self.bind((ip,port))
		self.listen(backlog)

		self.forwarder=forwarder
	def handle_accept(self):
		conn, addr = self.accept()
		print('accept')
		hostSelectorSocket(conn,self.forwarder)
	def closef(self):
		self.close()

class hostSelectorSocket(asyncore.dispatcher):
	def __init__(self,conn,forwarder):
		asyncore.dispatcher.__init__(self,conn)
		self.forwarder=forwarder
		self.received=False
	def handle_connect(self):
		pass
	def writable(self):
		return self.received
	def handle_read(self):
		read = self.recv(4096)
		res=parse('{host}:{port:d}\n',read.decode('utf-8'))
		if res:
			self.forwarder.updateRemote(res['host'],res['port'])
		self.received=True
	def handle_write(self):
		returnString=self.forwarder.getRemoteHost()+':'+str(self.forwarder.getRemotePort())+'\n'
		self.send(bytes(returnString,'utf-8'))
		self.close()
	def handle_close(self):
		self.close()
	

class receiver(asyncore.dispatcher):
	def __init__(self,conn):
		asyncore.dispatcher.__init__(self,conn)
		self.from_remote_buffer=bytes()
		self.to_remote_buffer=bytes()
		self.sender=None

	def handle_connect(self):
		pass

	def handle_read(self):
		read = self.recv(4096)
		# print '%04i -->'%len(read)
		self.from_remote_buffer += read

	def writable(self):
		return (len(self.to_remote_buffer) > 0)

	def handle_write(self):
		sent = self.send(self.to_remote_buffer)
		# print '%04i <--'%sent
		self.to_remote_buffer = self.to_remote_buffer[sent:]

	def handle_close(self):
		self.close()
		if self.sender:
			self.sender.close()

class sender(asyncore.dispatcher):
	def __init__(self, receiver, remoteaddr,remoteport):
		asyncore.dispatcher.__init__(self)
		self.receiver=receiver
		receiver.sender=self
		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		self.connect((remoteaddr, remoteport))

	def handle_connect(self):
		pass

	def handle_read(self):
		read = self.recv(4096)
		# print '<-- %04i'%len(read)
		self.receiver.to_remote_buffer += read

	def writable(self):
		return (len(self.receiver.from_remote_buffer) > 0)

	def handle_write(self):
		sent = self.send(self.receiver.from_remote_buffer)
		# print '--> %04i'%sent
		self.receiver.from_remote_buffer = self.receiver.from_remote_buffer[sent:]

	def handle_close(self):
		self.close()
		self.receiver.close()


ser = forwarder('127.0.0.1', 6600, 'localhost', 6601)
sel = hostSelector('127.0.0.1',6602, ser)
asyncore.loop()
