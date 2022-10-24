from socket import *
import sys
from packet import *

emulator_hostname = ""
emulator_port_number = 0
recevier_port_number = 0
output_file_name = ""

receiver_udpsocket = None

buffer = {}
# file_data = ""

def record_arrival_ack(data):
    
    ## ack.log
    log_file = open("arrival.log", "a+")
    # Content to be added
    content = str(data) + "\n"
    # Writing the file
    log_file.write(content)


def receive_ack():
    last_sequence = 31
    sequence_number = 0

    while(True):
        ack_packet_encode, serverAddress = receiver_udpsocket.recvfrom(2048)
        packet_ack_packet = Packet(ack_packet_encode)
        type, packet_seqnum, length, data = packet_ack_packet.decode()
        
        ## The sequence number is expecting
        if sequence_number == packet_seqnum:

            ##The packet is EOT packet
            if type == 2:
                EOT_packet = Packet(2, sequence_number, 0, "")
                receiver_udpsocket.sendto(EOT_packet.encode(),(emulator_hostname, emulator_port_number))
                record_arrival_ack("EOT")
                
                receiver_udpsocket.close()
                return
            
            ## None EOT packet but sequence number is expecting
            else:
                record_arrival_ack(packet_seqnum)
                ## First write to acket
                file = open(output_file_name, 'a+')
                file.write(data)
                last_sequence = sequence_number
                next_sequence_number = (sequence_number + 1) % 32

                while(True):
                    if next_sequence_number in buffer:
                        data = buffer.pop(next_sequence_number)
                        file.write(data)
                        last_sequence = next_sequence_number
                        next_sequence_number = (next_sequence_number + 1) % 32
                    else:
                        ## packet not exist
                        ## missing next_sequence_number
                        ack_packet =  Packet(0, last_sequence, 0, "")
                        receiver_udpsocket.sendto(ack_packet.encode(),(emulator_hostname, emulator_port_number))
                        sequence_number = next_sequence_number
                        break

        else:
            record_arrival_ack(packet_seqnum)
            ## within next 10 sequence number
            if sequence_number + 9 <= 31 and (packet_seqnum <= sequence_number + 9) and (packet_seqnum > sequence_number):
                buffer[packet_seqnum] = data

                

            elif packet_seqnum > sequence_number or packet_seqnum < (10 - (32 - sequence_number)):
                buffer[packet_seqnum] = data

            ## For both cases send ack for the most recently receieved in-order packet
            ack_packet =  Packet(0, last_sequence, 0, "")
            receiver_udpsocket.sendto(ack_packet.encode(),(emulator_hostname, emulator_port_number))
            sequence_number = next_sequence_number
            

if __name__ == "__main__":
    args = sys.argv[1:]
    if (len(args) != 4):
        print("In valid number of arguemnt")
        exit

    emulator_hostname = args[0]
    emulator_port_number = int(args[1])
    recevier_port_number = int(args[2])
    output_file_name = args[3]
    
    receiver_udpsocket = socket(AF_INET,SOCK_DGRAM)
    receiver_udpsocket.bind(('', recevier_port_number))
    receive_ack()

