from glob import glob
from socket import *
import sys
from packet import *
import threading



def record_log_sequence(data, timestamp):
    
    ## seqnum.log
    log_file = open("seqnum.log", "a+")
    # Content to be added
    content = "t=" + str(timestamp) + " " + str(data) + "\n"
    # Writing the file
    log_file.write(content)

def record_log_ack(data, timestamp):
    
    ## ack.log
    log_file = open("ack.log", "a+")
    # Content to be added
    content = "t=" + str(timestamp) + " " + str(data) + "\n"
    # Writing the file
    log_file.write(content)

def record_log_N(data, timestamp):

     ## ack.log
    log_file = open("N.log", "a+")
    # Content to be added
    content = "t=" + str(timestamp) + " " + str(data) + "\n"
    # Writing the file
    log_file.write(content)
    

emulator_host_name = ""
emulator_port_number = 0
sender_port_number = 0
time_out_interval = 0
file_name = ""

packet_dict = {}
current_data = ""
senderSocket_udp = None

timestamp = 0

## Initialize paramet
window_size_N = 1
record_log_N(window_size_N, timestamp)

sequence_number = 0
number_unack = 0
duplicate_count = 0
timer = None
timestamp += 1

lock = threading.Lock()

end_program = False


def cal_new_unack(sequence_number, ack_sequence):
    if sequence_number - ack_sequence - 1 >= 0:
        if sequence_number - ack_sequence == 1:
            return 0
        else:
            return sequence_number - ack_sequence - 1
    else:
        if abs(sequence_number - ack_sequence) == 31:
            return 0
        else:
            return (31 - ack_sequence) + sequence_number 

def timeout():
    global end_program
    global lock
    global window_size_N
    global timestamp
    global number_unack
    global packet_dict
    global emulator_host_name
    global emulator_port_number
    global sequence_number
    global timer
    global duplicate_count

    lock.acquire()
    if end_program == True:
        if timer != None:
            timer.cancel()
        lock.release()
        return


    ## Timeout happen
    window_size_N = 1
    duplicate_count = 0
    timestamp += 1
    record_log_N(window_size_N, timestamp)

    ## Event: Time out

    caused_timeout_sequence = 0
    
    ## Find the sequence number that caused the timeout
    if sequence_number - number_unack >= 0:
        caused_timeout_sequence = sequence_number - number_unack
    else:
        caused_timeout_sequence = 31 + 1 + (sequence_number - number_unack)
    
    if number_unack != 0:
        resend_packet = packet_dict[caused_timeout_sequence]
        ## Send packet (might need lock if concurrent)
        length_data = len(resend_packet.data)
        send_packet = Packet(1, caused_timeout_sequence, length_data, resend_packet.data)
        senderSocket_udp.sendto(send_packet.encode(),(emulator_host_name, emulator_port_number))
    
        record_log_sequence(caused_timeout_sequence, timestamp)

    ## restart the  timer
    if timer != None:
        timer.cancel()
    timer = threading.Timer(time_out_interval/1000, timeout)
    timer.start()

    lock.release()
    

def send_file():

    global emulator_host_name
    global emulator_port_number
    global sender_port_number
    global time_out_interval
    global file_name
    global packet_dict
    global current_data
    global senderSocket_udp
    global timestamp
    global window_size_N
    global sequence_number
    global number_unack
    global duplicate_count
    global timer
    global end_program

    lock = threading.Lock()

    file = open(file_name, 'r')
    while True:
         
        if current_data == "":
        ## No left over data, need to read from file

            # Read from file
            current_data = file.read(500)
            
            ## End of File
            if not current_data:
                lock.acquire()
                if number_unack == 0:
                    ## All ack has been received, can send EOT packet
                    EOT_packet = Packet(2, sequence_number, 0, "")
                    timestamp += 1
                    record_log_sequence(sequence_number, timestamp)

                    ## not sure should be update the sequence the number of not
                    senderSocket_udp.sendto(EOT_packet.encode(),(emulator_host_name, emulator_port_number))
                    lock.release()
                    end_program = True
                    if timer is not None:
                        timer.cancel()
                    break
                # else:
                    ## Still need to wait for un acks
                lock.release()

        lock.acquire()

        ## Sender has a packet to send and  Window is not full:
        if number_unack < window_size_N and current_data != "":
            
            ## Send packet (might need lock if concurrent)
            length_data = len(current_data)
            send_packet = Packet(1, sequence_number, length_data, current_data)

            packet_dict[sequence_number] = send_packet 
            senderSocket_udp.sendto(send_packet.encode(),(emulator_host_name, emulator_port_number))
            record_log_sequence(sequence_number, timestamp)
            
            ## Edit variable
            current_data = ""
            number_unack += 1
            timestamp += 1
            if end_program == False:
                sequence_number = (sequence_number + 1) % 32
            
            if timer == None:
                timer = threading.Timer(time_out_interval/1000, timeout)
                timer.start()

        lock.release() 
    return

def receive_ack():
    global emulator_host_name
    global emulator_port_number
    global sender_port_number
    global time_out_interval
    global file_name
    global packet_dict
    global current_data
    global senderSocket_udp
    global timestamp
    global window_size_N
    global sequence_number
    global number_unack
    global duplicate_count
    global timer

    while(True):

     ## Sender receive acknowlegement packet
        ack_packet_encode, serverAddress = senderSocket_udp.recvfrom(2048)
        ack_packet = Packet(ack_packet_encode)
        type, ack_seqnum, length, data = ack_packet.decode()

        lock.acquire()
        record_log_ack(ack_seqnum, timestamp)

        ## Event: Receive packet
        timestamp += 1
        lock.release()

        ## Check ack number 
        if type == 0:
            lock.acquire()
            ## check whether timeout or not (i.e timer 3 duplicates ack)
            if sequence_number - number_unack >= 1:
                if sequence_number - number_unack  - 1 ==  ack_seqnum:
                    if end_program == True:
                        lock.release()
                        continue
                    duplicate_count += 1

                    if duplicate_count == 3:
                        retransmit_seq_number = (ack_seqnum + 1) % 32
                        window_size_N = 1
                        
                        resend_packet = packet_dict[retransmit_seq_number]
                        ## Send packet (might need lock if concurrent)
                        length_data = len(resend_packet.data)
                        send_packet = Packet(1, retransmit_seq_number, length_data, resend_packet.data)
                        senderSocket_udp.sendto(send_packet.encode(),(emulator_host_name, emulator_port_number))
                        
                        ## record two log at same time
                        record_log_N(window_size_N, timestamp)
                        record_log_sequence(retransmit_seq_number, timestamp)

                         ## Event: Timeout due to duplicate
                        timestamp += 1

                        ## restart the timer
                        if timer != None:
                            timer.cancel()
                        timer = threading.Timer(time_out_interval/1000, timeout)
                        timer.start()
                else:
                    ## new ack
                    duplicate_count = 0
                    if number_unack != 0:
                        ## Restart timer
                        if timer != None:
                            timer.cancel()
                        timer = threading.Timer(time_out_interval/1000, timeout)
                        timer.start()
                    else:
                        if timer != None:
                            timer.cancel()
                        timer = None
                    
                    ## Increment window size when new ack
                    window_size_N = min(window_size_N+1, 10)
                    record_log_N(window_size_N, timestamp)
                    number_unack = cal_new_unack(sequence_number, ack_seqnum)
            

            else:
                if 31 - (sequence_number - number_unack) ==  ack_seqnum:
                    if end_program == True:
                        lock.release()
                        continue
                    duplicate_count += 1

                    if duplicate_count == 3:
                        # sequence_number = (ack_seqnum + 1) % 32
                        retransmit_seq_number = (ack_seqnum + 1) % 32
                        window_size_N = 1
                        

                        resend_packet = packet_dict[retransmit_seq_number]
                        ## Send packet (might need lock if concurrent)
                        length_data = len(resend_packet.data)
                        send_packet = Packet(1, retransmit_seq_number, length_data, resend_packet.data)
                        senderSocket_udp.sendto(send_packet.encode(),(emulator_host_name, emulator_port_number))

                        ## record two log at same time
                        record_log_sequence(retransmit_seq_number, timestamp)
                        record_log_N(window_size_N, timestamp)

                        ## Event: Timeout due to duplicate
                        timestamp += 1

                        ## restart the timer
                        if timer != None:
                            timer.cancel()
                        timer = threading.Timer(time_out_interval/1000, timeout)
                        timer.start()
                else:
                    ## new ack
                    duplicate_count = 0
                    if number_unack != 0:
                        ## restart timer
                        if timer != None:
                            timer.cancel()
                        timer = threading.Timer(time_out_interval/1000, timeout)
                        timer.start()
                    else:
                        if timer != None:
                            timer.cancel()
                        timer = None
                    
                    ## Increment window size when new ack
                    window_size_N = min(window_size_N+1, 10)
                    record_log_N(window_size_N, timestamp)
                    number_unack = cal_new_unack(sequence_number, ack_seqnum)
            lock.release()
        elif type == 2:
            ## EOT event
            if timer is not None:
                timer.cancel()
            # wait for EOT
            lock.acquire()
            record_log_sequence("EOT",timestamp)
            lock.release()
            
            senderSocket_udp.close()
            
            return
        else:
            exit(1)


if __name__ == "__main__":
    args = sys.argv[1:]
    if (len(args) != 5):
        print("Incorrect number of arg")
        exit
    emulator_host_name = args[0]
    emulator_port_number = int(args[1])
    sender_port_number = int(args[2])
    time_out_interval = int(args[3])
    file_name = args[4]

    ##  creat the UDP socket 
    senderSocket_udp = socket(AF_INET,SOCK_DGRAM)
    senderSocket_udp.bind(('', sender_port_number))

    # create two new threads
    t1 = threading.Thread(target=send_file)
    t2 = threading.Thread(target=receive_ack)

    # start the threads
    t1.start()
    t2.start()

    # wait for the threads to complete
    t1.join()
    t2.join()

    end_program = True
    exit(1)
