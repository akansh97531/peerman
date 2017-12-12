import threading
import time
import multiprocessing
import os
import socket
import random
import Queue
IP = '127.0.0.1'
dataToSend="Hello World"
dataToSendSize=11
dataToSendIter=0
sendDataPort = None
receiveAckPort = None
receiveAckSocket = None
SendDataSock =None
TIMEOUT=5
MAX_PACKETS=8
dataPackets = [None for i in range(MAX_PACKETS)]
nextDataToCompress=0
nextPacketToSend=0
sendingLastBlock=None
packetSentAndAck=7
compressedBlock=None
isCompressed=False
file=None
chuck_size=None
sent_bytes=0
c = threading.Condition()
c1 = threading.Condition()
c2 = threading.Condition()
c3 = threading.Condition()
ackQueue=Queue.Queue()
class SendDataThread(threading.Thread):
	def __init__(self,name):
		threading.Thread.__init__(self)
		self.name = name

	def run(self):
		global MAX_PACKETS
		global dataPackets
		global nextPacketToSend
		global packetSentAndAck
		global TIMEOUT
		while(True):
			c.acquire()
			# print 'C Acquired by SendDataThread'
			# print "here",dataPackets[0],nextPacketToSend,packetSentAndAck
			# print "h"
			while nextPacketToSend==packetSentAndAck:
				# print 'C Wait in SendDataThread'
				c.wait(TIMEOUT)
				# print 'C Notified in SendDataThread'
				if(nextPacketToSend==packetSentAndAck):
					send(dataPackets[(packetSentAndAck+1)%MAX_PACKETS])
			c2.acquire()
			# print 'C2 Acquired by SendDataThread'
			if dataPackets[nextPacketToSend]==None:
				c2.notifyAll()
				# print 'C2 Notified by SendDataThread'
				# print 'C2 Wait in SendDataThread'
				c2.wait()
				# print 'C2 Notified in SendDataThread'
			while dataPackets[nextPacketToSend]==None:
				# print 'C2 Wait in SendDataThread'
			 	c2.wait()
			# print 'C2 Notified in SendDataThread'
			c2.release()
			# print 'C2 Released by SendDataThread'
			send(dataPackets[nextPacketToSend])	#TODO
			nextPacketToSend+=1
			nextPacketToSend%=MAX_PACKETS
			c.notifyAll()
			# print 'C Notified by SendDataThread'
			c.release()
			# print 'C Released by SendDataThread'

class ReceiveAckThread(threading.Thread):
	def __init__(self,name):
		threading.Thread.__init__(self)
        # self.name = name

	def run(self):
		global MAX_PACKETS
		global dataPackets
		global nextPacketToSend
		global packetSentAndAck
		global sendingLastBlock
		p = threading.Thread(target=recvAck, args=())
		p.start()
		while True:
			ackReceived=ackQueue.get()	#TODO
			ackQueue.task_done()
			#print 'Ack Recv',ackReceived,sendingLastBlock
			c3.acquire()
			if ackReceived == sendingLastBlock:
				print 'Final Ack Rec'
				c3.notifyAll()
			c3.release()
			c.acquire()
			# print 'C Acquired by ReceiveAckThread'
			c1.acquire()
			# print 'C1 Acquired by ReceiveAckThread'
			packetSentAndAck+=1
			packetSentAndAck%=MAX_PACKETS
			while packetSentAndAck!=ackReceived:
				dataPackets[packetSentAndAck]=None
				packetSentAndAck+=1
				packetSentAndAck%=MAX_PACKETS
			dataPackets[packetSentAndAck]=None
			c.notifyAll()
			# print 'C1 Notified by ReceiveAckThread'
			c1.notifyAll()
			# print 'C Notified by ReceiveAckThread'
			c.release()
			# print 'C Released by ReceiveAckThread'
			c1.release()
			# print 'C1 Released by ReceiveAckThread'

class CompressDataThread(threading.Thread):
	def __init__(self,name):
		threading.Thread.__init__(self)
		# self.name = name

	def run(self):
		global MAX_PACKETS
		global dataPackets
		global nextPacketToSend
		global nextDataToCompress
		global packetSentAndAck
		global compressedBlock
		global isCompressed
		global sendingLastBlock
		while(True):
			# print 'comp'
			c1.acquire()
			# print 'C1 Acquired by CompressDataThread'
			# while nextDataToCompress==packetSentAndAck:
			# 	c1.wait()
			while dataPackets[nextDataToCompress]!=None:
				# print 'C1 Wait in CompressDataThread'
				c1.wait()

			# print 'C1 Notified in CompressDataThread'

			c1.release()
			# print 'C1 Released by CompressDataThread'
			#run LZ4 compr. thread
			'''
			compressed=False
			data=getNextOriginalData() #TODO 
			dataOriginal=data
			compressor = multiprocessing.Process(target=LZ4CompressionProcessManager,args=(compressed,data))
			compressor.start()
			print 'h22'
			c2.acquire()
			c2.wait()
			compressor.terminate()
			print 'h33'
			'''
			#stopLZ4 if running
			c2.acquire()
			# print 'C2 Acquired by CompressDataThread'
			isCompressed=False
			compressedBlock=getNextOriginalData()
			# print 'Next Data : ',nextDataToCompress,compressedBlock
			# c2.release()
			# print 'C2 Released by CompressDataThread'
			# c2.acquire()
			# print 'C2 Acquired by CompressDataThread'
			t=LZ4CompressionProcessManager("Rec")
			# t.daemon = True
			t.start()
			# print 'C2 Wait in CompressDataThread'
			c2.wait()
			# print 'C2 Notified in CompressDataThread'

			if t.isAlive():
				t.join(0)

			# if(isCompressed):
			# 	data=dataOriginal

			c1.acquire()
			# print 'C1 Acquired by CompressDataThread'
			dataPackets[nextDataToCompress]=getBlock(nextDataToCompress,isCompressed,compressedBlock)	#TODO
			c2.notifyAll()
			# print 'C2 Notified by CompressDataThread'
			c2.release()
			# print 'C2 Released by CompressDataThread'
			nextDataToCompress+=1
			nextDataToCompress%=MAX_PACKETS
			c1.notifyAll()
			# print 'C1 Notified by CompressDataThread'
			c1.release()
			# print 'C1 Released by CompressDataThread'
			c3.acquire()
			if sendingLastBlock!=None:
				c3.release()
				break
			c3.release()


class LZ4CompressionProcessManager(threading.Thread):
	def __init__(self,name):
		threading.Thread.__init__(self)
        # self.name = name

	def run(self):
		global isCompressed
		global compressedBlock
		dataNew=compressLZ4(compressedBlock)	#TODO
		c2.acquire()
		# print 'C2 Acquired by LZ4CompressionProcessManager'
		compressedBlock=dataNew
		isCompressed=True
		c2.notifyAll()
		# print 'C2 Notified by LZ4CompressionProcessManager'
		c2.release()
		# print 'C2 Released by LZ4CompressionProcessManager'


def getNextOriginalData():
	'''
	return os.urandom(10)
	'''
	global sent_bytes
	global file
	d=file.read(chunk_size)

	if(len(d)>0):
		sent_bytes+=len(d)
		return d
	else:
		return None
	# if dataToSendIter==dataToSendSize:
	# 	return None
	# d=dataToSend[dataToSendIter]
	# dataToSendIter+=1
	# return d
	

def getBlock(sequence,compressed,data):

	if data==None:
		hashvalue=15
		global sendingLastBlock
		c3.acquire()
		sendingLastBlock=sequence
		c3.release()
	else:
		hashvalue=int(getHash(data))
	sequence*=2
	if compressed:
		sequence+=1
	b=bytes(bytearray([(sequence<<4)+hashvalue]))
	print b
	return b[0]+bytes(data)
def getHash(data):
	return 0

def compressLZ4(data):
	# time.sleep((random.random()*5000)+2000)
	if data==None:
		return None
	return data

def send(data):
	# print "sending"
	global IP
	global sendDataPort
	global SendDataSock
	SendDataSock.sendto(data,(IP,sendDataPort))
def recvAck():
	global sendingLastBlock
	while True:
		data, addr=receiveAckSocket.recvfrom(16)
		s=int(data[0].encode('hex'), 16)
		print "Ack : ",s
		ackQueue.put(s)
		if s==sendingLastBlock:
			print 'Last Block'
			break


def send_data(f,chunk):
	global file
	global chunk_size
	chunk_size=chunk
	file=f
	t1=CompressDataThread("compress")
	t1.daemon=True
	t1.start()
	time.sleep(1)
	t2=SendDataThread("send")
	t2.daemon=True
	t2.start()
	t3=ReceiveAckThread("Rec")
	t3.daemon=True
	t3.start()

	c3.acquire()
	c3.wait()
	c3.release()
	print 'transmission'
	t1.join(0)
	t2.join(0)
	t3.join(0)

