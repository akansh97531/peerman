
try:
    from Tkinter import *
except :
    from tkinter import *

try:
    import ttk
except :
    from tkinter import ttk

try:
    from tkinter.filedialog import *
    from tkinter.messagebox import *
except :
    from tkFileDialog import *
    from tkMessageBox import *
import threading


import os
import sys
import socket
from select import select
import struct
import miniupnpc
import time
import protocol
import protocol_client



global target

file_size=0
chunk_size=10240
file_name=""
data_port = 45678
ack_port = 45677



def recv():
    global file_size
    global file_name
    global f
    protocol_client.IP = target[0]
    protocol_client.receiveDataPort = data_port
    protocol_client.sendAckPort = ack_port
    protocol_client.receiveDataSocket = sockfd
    protocol_client.sendAckSocket = sockfd_ack
    upnp = miniupnpc.UPnP()
    #upnp.discoverdelay = 10

    total_chunks=file_size/chunk_size

    if upnp.discover()>0:
        upnp.selectigd()
        try:
            upnp.deleteportmapping(data_port,"UDP")
        except :
            print("port not in used")
        # addportmapping(external-port, protocol, internal-host, internal-port, description, remote-host)
        upnp.addportmapping(data_port, 'UDP', upnp.lanaddr, data_port, 'peerman', '')

        try:
            upnp.deleteportmapping(ack_port,"UDP")
        except :
            print("port not in used")
        # addportmapping(external-port, protocol, internal-host, internal-port, description, remote-host)
        upnp.addportmapping(ack_port, 'UDP', upnp.lanaddr, ack_port, 'peerman', '')
        

    # Establish connection with client.
    #print 'Got connection from', addr

    ### receive header
    l = ""
    flag=0

    l,addr = sockfd.recvfrom(chunk_size)
    print "Receiving...",l
    if l[0]=="#" and flag==0:
        st=l.split("#")
        file_size=int(st[1])
        file_name=st[2]
        f = open(os.path.join(os.path.dirname(sys.argv[0]), file_name),'wb')
        flag=1

    protocol_client.recv_data(f,chunk_size)

    # while (True):
    #     l,addr = sockfd.recvfrom(chunk_size)
    #     print "Receiving...",l
    #     i_max+=len(l)

    #     if(i_max > 0.97 * file_size):
    #         exit_flag=1
    #         break
    #     f.write(l)
        #print "received :  ",l

    i_max+=chunk_size
    f.close()
    print "Done Receiving"
    sockfd.sendto('Thank you for connecting',target)
    sockfd.close() 



def send():
    protocol.sendDataPort = data_port
    protocol.receiveAckPort = ack_port
    protocol.receiveAckSocket = sockfd_ack
    protocol.SendDataSock = sockfd
    protocol.IP = target[0]
    global i_max
    global file_size
    #sockdata = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
    #sockdata.connect((target[0], port_))
    f = open( file_name ,'rb')
    file_size = os.path.getsize(file_name )
    file_temp = file_name.split("/")
    print file_temp[-1]

    ## send file header
    sockfd.sendto("#"+str(file_size)+"#"+file_temp[-1],target)
    time.sleep(.5)
    print 'Sending...'

    protocol.send_data(f,chunk_size)


    # l = f.read(chunk_size)
    # while (l):
    #     print 'Sending...',l
    #     sockfd.sendto(l,target)
    #     l = f.read(chunk_size)
    #     time.sleep(.1)
    #     i_max+=len(l)

    # i_max+=chunk_size
    # sockfd.sendto("$",target)
    f.close()
    print "Done Sending"
    print sockfd.recvfrom(1024)
    sockfd.close() 

class myThread (threading.Thread):
    """
    custom thread to run download thread
    """
    def __init__(self,s_or_r):
        self.s_or_r=s_or_r
        threading.Thread.__init__(self)

    def run(self):
        """
        function called when thread is started
        """
        if self.s_or_r=='s':
            send()
        else:
            recv()


class progress_class():
    """
    custom class for profress bar
    """
    def __init__(self, frame, s_or_r):
        self.frame = frame
        self.s_or_r=s_or_r
        # initialize progressbar
        self.progress=ttk.Progressbar(frame, orient="horizontal", 
                             length=300, mode="determinate")
        self.progress.pack()
        self.str=StringVar()
        self.label=Label(frame, textvariable=self.str, width=70)
        self.label.pack()
        self.progress["value"] = 0
        self.bytes=0
        self.maxbytes=0
        # start thread
        self.start()


    def start(self):
        """
        function to initialize thread for downloading
        """
        self.thread=myThread(  self.s_or_r )

        self.progress["value"] = 0
        self.bytes = 0
        self.thread.start()

        self.read_bytes()


    def read_bytes(self):
        """
        reading bytes; update progress bar after 1 ms
        """
        global exit_flag
        exit_flag=0
        if self.s_or_r=="s":
            self.bytes = protocol.sent_bytes
        else:
            self.bytes = protocol_client.received_bytes
        self.maxbytes = file_size
        self.progress["maximum"] = file_size
        self.progress["value"] = self.bytes
        #print self.bytes
        self.str.set(file_name+ "   " + str(self.bytes)
                                  + "B / " + str(int(self.maxbytes+ 1)) + " B")
        #print i_max,file_size
        if exit_flag==1 :
            self.progress["maximum"] = file_size
            self.progress["value"] = file_size
            time.sleep(.6)
            self.frame.destroy()
        else:
            self.frame.after(1, self.read_bytes)


def bytes2addr( bytes ):
    """Convert a hash to an address pair."""
    if len(bytes) != 6:
        raise ValueError, "invalid bytes"
    host = socket.inet_ntoa( bytes[:4] )
    port, = struct.unpack( "H", bytes[-2:] )
    return host, port

def connect(server_add,server_port,server_pool):
    global target
    global sockfd
    global sockfd_ack

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))

    try:
        master = (server_add, int(server_port) )
        pool = server_pool
    except (IndexError, ValueError):
        print >>sys.stderr, "usage: %s <host> <port> <pool>" % sys.argv[0]
        sys.exit(65)
    sockfd = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
    sockfd_ack = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )

    sockfd.bind(("",data_port))
    sockfd_ack.bind(("",ack_port))

    sockfd.sendto( pool +"#"+str(s.getsockname()[0])+"#"+str(sockfd.getsockname()[1]) , master )
    print (master,sockfd.getsockname())

    data, addr = sockfd.recvfrom( len(pool)+50 )
    if data != "ok "+pool:
        print >>sys.stderr, "unable to request!"
        sys.exit(1)
    sockfd.sendto( "ok", master )
    print >>sys.stderr, "request sent, waiting for parkner in pool '%s'..." % pool
    data, addr = sockfd.recvfrom( 100 )
    temp = data.split("#")
    target = (temp[0],int(data_port) )
    print >>sys.stderr, "connected to ", target

    s.close()

    #return target



class makeform:


    def __init__(self, root , server_add, server_port, server_pool):

        self.server_add= server_add
        self.server_port=server_port
        self.server_pool=server_pool
        self.root=root

        # connect button
        self.row2 = Frame(root)
        self.connect_button = Button(self.row2, width = 30, text = "Connect", anchor = 'w')
        self.connect_button.bind('<Button-1>', self.connect_func)
        self.row2.pack(side = TOP, fill = X, padx = 5, pady = 5)
        self.connect_button.pack(side = LEFT)

        #connect label
        # self.label_connect=Label(self.row2, textvariable=str_connect, width=40)
        # self.label_connect.pack(side = RIGHT)

        # send button
        self.row1 = Frame(root)
        self.send_button = Button(self.row1, width = 30, text = "Send", anchor = 'w')
        self.send_button.bind('<Button-1>', self.send_func)
        self.row1.pack(side = TOP, fill = X, padx = 5, pady = 5)
        self.send_button.pack(side = LEFT)

        # receive button
        self.recv_button = Button(self.row1, width = 30, text = "Receive", anchor = 'w')
        self.recv_button.bind('<Button-1>', self.recv_fun)
        self.recv_button.pack(side = RIGHT)

    def connect_func(self,event):
        self.t1 = threading.Thread(target = connect,  args = (self.server_add,self.server_port,self.server_pool) )
        self.t1.start()
        self.t1.join()
        print "connected"

    def send_func(self,event):
        global file_name

        frame= Frame(self.root)
        frame.pack()
        file_name= askopenfilename()
        progress_class(frame,"s")
        print "Send"

    def recv_fun(self,event):
        frame= Frame(self.root)
        frame.pack()
        progress_class(frame,"r")
        print "Receive"



def main():
    global target
    global file_name
    connect( sys.argv[1], sys.argv[2], sys.argv[3].strip() )    

    while True:
        inp = raw_input()
        print inp
        if inp == "r":
            recv()

        elif inp == "s":
            file_name = os.path.join(os.path.dirname(sys.argv[0]), "tt.mp3")
            send()


    sockfd.close()

if __name__ == "__main__":

    main()

    # root = Tk()
    # root.wm_title("peerman")

    # makeform(root, sys.argv[1], sys.argv[2], sys.argv[3].strip())
    # root.mainloop()


    

# python client2.py 13.126.90.141 4653 "abc" "r" ('13.126.90.141', 4653)
# sudo ssh -i vaibhav.pem ubuntu@ec2-35-154-215-193.ap-south-1.compute.amazonaws.com
# sudo ssh -i "akansh97531.pem" ubuntu@ec2-13-126-90-141.ap-south-1.compute.amazonaws.com
# requirements miniupnpc python-tk