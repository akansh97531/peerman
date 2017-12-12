import threading
import time
import multiprocessing
import os
import socket
import Queue
import random



from sys import  stderr

import lz4framed

IP = None
receiveDataPort = None
sendAckPort = None
receiveDataSocket = None
sendAckSocket = None
dataReceived= Queue.Queue()
dataAligned = Queue.Queue()
totalDataReceived=0
TIMEOUT=0.5
MAX_PACKETS=8
dataPackets = [None for i in range(MAX_PACKETS)]
isCompressed = [None for i in range(MAX_PACKETS)]
hashValue = [None for i in range(MAX_PACKETS)]
nextSeq = 0
c = threading.Condition()
transferComplete = threading.Condition()
file=None
received_bytes=0
chunk_size=1024
header_size=30
class ReceiveDataThread(threading.Thread):
    def __init__(self,name):
        threading.Thread.__init__(self)
        self.name = name

    def run(self):
        global MAX_PACKETS
        global dataPackets
        global nextPacketToSend
        global packetSentAndAck
        global totalDataReceived
        global TIMEOUT
        while(True):
            data, addr=receiveDataSocket.recvfrom(chunk_size+header_size)
            totalDataReceived+=len(data)
            dataReceived.put(data)
            #print 'Recv : ',data
            s=int(data[0].encode('hex'), 16)
            hashv=s%16
            # if hashv==15:
            #     break
            

class processDataThread(threading.Thread):
    def __init__(self,name):
        threading.Thread.__init__(self)
        self.name = name

    def run(self):
        global dataPackets
        global isCompressed
        global hashValue
        while(True):
            data=dataReceived.get()
            s=int(data[0].encode('hex'), 16)
            data=data[1:]
            hashv=s%16
            s/=16
            compressed=s%2
            s/=2
            sequence=s%8
            if verify(data,hashv)==False:
                dataReceived.task_done()
                pass
            c.acquire()
            dataPackets[sequence]=data
            isCompressed[sequence]=compressed
            hashValue[sequence]=hashv
            c.notifyAll()
            c.release()
            dataReceived.task_done()
            if hashv==15:
                break

class alignDataThread(threading.Thread):
    def __init__(self,name):
        threading.Thread.__init__(self)
        self.name = name

    def run(self):
        global dataPackets
        global isCompressed
        global hashValue
        global nextSeq
        global MAX_PACKETS
        while True:
            c.acquire()
            while dataPackets[nextSeq]==None :
                c.wait()
            while dataPackets[nextSeq]!=None :
                lastSeqAligned = nextSeq
                if hashValue[nextSeq]==15:
                    dataAligned.put(None)
                if isCompressed[nextSeq] :
                    dataAligned.put(decompress(dataPackets[nextSeq]))
                else:
                    dataAligned.put(dataPackets[nextSeq])
                dataPackets[nextSeq]=None
                isCompressed[nextSeq]=None
                hashValue[nextSeq]=None
                nextSeq+=1
                nextSeq%=MAX_PACKETS
            c.notifyAll()
            c.release()
            sendAck(lastSeqAligned)


class saveDataThread(threading.Thread):
    def __init__(self,name):
        threading.Thread.__init__(self)
        self.name = name

    def run(self):
        while True:
            data=dataAligned.get()
            saveToFile(data)
            if data==None:
                transferComplete.acquire()
                transferComplete.notifyAll()
                transferComplete.release()
            dataAligned.task_done()


def decompress(data):
    if len(data)>0:
    	try:
            data=lz4framed.decompress(data)
        except:
            print  'error : ',data   
    else:
        data=None
    return data
def verify(hashv,data):
    if hashv==15:
        return True
    return True
def sendAck(sequence):
    # print 'Sending Ack : ',sequence
    sendAckSocket.sendto(bytes(bytearray([sequence])) , (IP,sendAckPort))
def saveToFile(data):
    global file
    global received_bytes
    if data==None:
        print 'None'
    else:
        file.write(data)
        received_bytes+=len(data)
    #print data


def recv_data(f,chunk):
    global file
    global chunk_size
    chunk_size=chunk
    file=f
    t1=ReceiveDataThread("Rec")
    t1.daemon=True
    t1.start()
    t2=alignDataThread("send")
    t2.daemon=True
    t2.start()
    t3=saveDataThread("Rec")
    t3.daemon=True
    t3.start()
    t4=processDataThread("Rec")
    t4.daemon=True
    t4.start()

    transferComplete.acquire()
    transferComplete.wait()
    transferComplete.release()
    print 'transmission done'
    t1.join(0)
    t2.join(0)
    t3.join(0)
    t4.join(0)






'''

import socket
IP = '127.0.0.1'
receiveDataPort = 5005
sendAckPort = 5006
receiveDataSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
sendAckSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
receiveDataSocket.bind((IP,receiveDataPort))
while True:
    data, addr=receiveDataSocket.recvfrom(1024)
    # d=list(data)
    s=int(data[0].encode('hex'), 16)
    data=data[1:]
    hashValue=s%16
    s/=16
    isCompressed=s%2
    s/=2
    sequence=s%8
    print "Data : ",data,sequence,isCompressed,hashValue
    sendAckSocket.sendto(bytes(bytearray([sequence])) , (IP,sendAckPort))
'''