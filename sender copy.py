from socket import *
import sys
from packet import *
import time



def record_log_sequence(data, timestamp):
    
    ## seqnum.log
    log_file = open("seqnum.log", "a+")
    # Content to be added
    content = str(data) + "\n"
    # Writing the file
    log_file.write(content)

def record_log_sequence(data, timestamp):
    
    ## ack.log
    log_file = open("ack.log", "a+")
    # Content to be added
    content = str(data) + "\n"
    # Writing the file
    log_file.write(content)

def record_log_N(data, timestamp):

     ## ack.log
    log_file = open("ack.log", "a+")
    # Content to be added
    content = str(data) + "\n"
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
timer_ms = None
duplicate_count = 0


def send_file():



    file = open(file_name, 'r')

    while True:
         
        # Read from file
        current_data = file.read(500)

        ## End of File
        if current_data is not "":
            if number_unack == 0:
                ## All ack has been received, can send EOT packet
                EOT_packet = Packet(2, sequence_number, 0, "EOT")
                senderSocket_udp.sendto(EOT_packet.encode(),emulator_host_name, emulator_port_number)
                break
            else:
                ## Still need to wait for un acks
                print("number_unack",number_unack)

        
        ## Sender has a packet:
        if number_unack < window_size_N:
            ## Window is not full
            
            ## Send packet (might need lock if concurrent)
            length_data = len(current_data)
            send_packet = Packet(1, sequence_number, length_data, current_data)

            packet_dict[sequence_number] = send_packet
            
            senderSocket_udp.sendto(send_packet.encode(),emulator_host_name)
            
            ## Edit variable
            current_data = ""
            number_unack += 1
            timestamp += 1
            sequence_number = (sequence_number + 1) % 32
            
            if (timer_ms == None):
                timer_ms = int(round(time.time() * 1000))
        
        ## Window is full will send later
        else:
            ## need to due with this data later first before grabbing new data
            current_data = current_data

        ## check whether timeout or not
        if timer_ms is not None and int(round(time.time() * 1000)) - timer_ms  > time_out_interval:
            ## Timeout happen
            window_size_N = 1
            timestamp += 1

            ## Event: Time out
            timestamp += 1

            caused_timeout_sequence = 0
            ## Find the sequence number that caused the timeout
            if sequence_number - number_unack > 0:
                caused_timeout_sequence = sequence_number - number_unack
            else:
                caused_timeout_sequence = 31 + 1 - (sequence_number - number_unack)
            
            resend_packet = packet_dict[caused_timeout_sequence]
            ## Send packet (might need lock if concurrent)
            length_data = len(resend_packet)
            send_packet = Packet(1, caused_timeout_sequence, length_data, resend_packet)
            senderSocket_udp.sendto(send_packet.encode(),emulator_host_name)

            ## restart the timer
            timer_ms = int(round(time.time() * 1000))


    
def receive_ack():

    while(True):

     ## Sender receive acknowlegement packet
        ack_packet_encode, serverAddress = senderSocket_udp.recvfrom(2048)
        type, ack_seqnum, length, data = ack_packet_encode.decode()

        ## Event: Receive packet
        timestamp += 1

        ## Check ack number 
        if type == 0:
            ## check whether timeout or not (i.e timer run out or 3 duplicates ack)
            if sequence_number - number_unack > 0:
                if sequence_number - number_unack  - 1 ==  ack_seqnum:
                    duplicate_count += 1

                    if duplicate_count == 3:
                        sequence_number = ack_seqnum + 1
                        window_size_N = 1

                        ## Event: Timeout due to duplicate
                        timestamp += 1

                        resend_packet = packet_dict[sequence_number]
                        ## Send packet (might need lock if concurrent)
                        length_data = len(resend_packet)
                        send_packet = Packet(1, sequence_number, length_data, resend_packet)
                        senderSocket_udp.sendto(send_packet.encode(),emulator_host_name)

                        ## restart the timer
                        timer_ms = int(round(time.time() * 1000))
                else:
                    ## new ack
                    if number_unack != 0:
                        timer_ms = int(round(time.time() * 1000))
                    else:
                        timer_ms = None
                    
                    ## Increment window size when new ack
                    window_size_N = min(window_size_N+1, 10)
                    number_unack -= 1
            

            else:
                if 31 - (sequence_number - number_unack) ==  ack_seqnum:
                    duplicate_count += 1

                    if duplicate_count == 3:
                        sequence_number = ack_seqnum + 1
                        window_size_N = 1

                        ## Event: Timeout due to duplicate
                        timestamp += 1

                        resend_packet = packet_dict[sequence_number]
                        ## Send packet (might need lock if concurrent)
                        length_data = len(resend_packet)
                        send_packet = Packet(1, sequence_number, length_data, resend_packet)
                        senderSocket_udp.sendto(send_packet.encode(),emulator_host_name)
                        ## restart the timer
                        timer_ms = int(round(time.time() * 1000))
                else:
                    ## new ack
                    if number_unack != 0:
                        timer_ms = int(round(time.time() * 1000))
                    else:
                        timer_ms = None
                    
                    ## Increment window size when new ack
                    window_size_N = min(window_size_N+1, 10)
                    number_unack -= 1
        else:
            print("Get Non ack type in ack packet")
            exit(1)


        # wait for EOT
        eot, addr = senderSocket_udp.recvfrom(2048)

        ## Event: Receive packet
        timestamp += 1

        senderSocket_udp.close()



 
        





if __name__ == "__main__":
    args = sys.argv[1:]
    if (len(args) != 5):
        print("In valid number of arguemnt")
        exit
    emulator_host_name = args[2]
    emulator_port_number = int(args[3])
    sender_port_number = int(args[4])
    time_out_interval = args[5]
    file_name = args[6]

    ##  creat the UDP socket 
    senderSocket_udp = socket(AF_INET,SOCK_DGRAM)
    senderSocket_udp.bind(('', sender_port_number))

    send_file()

    return
