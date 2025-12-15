from dataclasses import dataclass
from typing import Dict, List
import sys
import math
import time
import random

#in this experiment there are 32 frames in physical memory
NUM_FRAMES = 32

#define the frames, i.e. the vpns that are stored in memory
frames = [None] * NUM_FRAMES

#this is establishing a set of stats per algorithm for easy referencing later
stats_dispatch = {
    "RAND": {"page_faults": 0, "disk_accesses": 0, "dirty_writes": 0},
    "FIFO": {"page_faults": 0, "disk_accesses": 0, "dirty_writes": 0},
    "LRU": {"page_faults": 0, "disk_accesses": 0, "dirty_writes": 0},
    "PER": {"page_faults": 0, "disk_accesses": 0, "dirty_writes": 0},
    "oracle": {"page_faults": 0, "disk_accesses": 0, "dirty_writes": 0},

}

stats = None


#initalize a global variable to track the first free frame (just optimizes the initial loading)
free_frame = None
access_time = 0


#define table of all page mappings
page_table = {}

#Initialize memory access variables to a global state so they can be used inside of the below algorithms
pid = None
vpn = None
access = None

def reset_state(num_frames=NUM_FRAMES):
    global page_table, frames
    page_table = {}
    frames = [None] * num_frames


def RAND_victim(pte):
    pass

def FIFO_victim(pte):
    oldest_frame = 0
    for i in NUM_FRAMES:
        if frames[i]["load_time"] < frames[oldest_frame]["load_time"]:
            oldest_frame = i
    if frames[oldest_frame]["dirty"]:
        stats["disk_accesses"] += 1
        stats["dirty_writes"] += 1
    
    

def LRU_victim(pte):
    pass

def PER_victim(pte):
    pass

def oracle_victim(pte):
    pass

victim_dispatch = {
    "RAND": RAND_victim,
    "FIFO":FIFO_victim,
    "LRU":LRU_victim,
    "PER": PER_victim,
    "oracle": oracle_victim
}

victim_func = None


alg_list = ['RAND', 'FIFO', 'LRU', 'PER', 'oracle']

input_file = sys.argv[1]
#algorithm = sys.argv[2]
[

#This loop iterates through the selected file. It is given an algorithm and then processes each memory access one at a time.
def algorithm_loop(algorithm):
    print(f"Running: {algorithm}")
    access_time = 0
    victim_func = victim_dispatch[algorithm]
    stats = stats_dispatch[algorithm]
    with open(input_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line: continue

            parts = line.split()
            pid = int(parts[0])
            vpn = int(parts[1])
            access = parts[2]
            
            free_frame = None
            for i in range(NUM_FRAMES):
                if frames[i] is None:
                    free_frame = i
                    frames[free_frame] = {
                        "pid": pid,
                        "vpn": vpn,
                        "ref": True,
                        "dirty": (access != "R"),
                        "load_time": access_time,
                        "last_used": access_time
                    }
                    stats["page_faults"] += 1
                    stats["disk_accesses"] += 1

            #if the given process isn't in the page table, add it to the page table
            if pid not in page_table:
                page_table[pid] = {}

            #if the virtual page number for this process isn't present, create it
            if vpn not in page_table[pid]:
                page_table[pid][vpn] = {
                        'valid': False,
                        'frame': None,
                        'dirty': False
                }
                    
            pte = page_table[pid].get(vpn)
            
            if pte is not None and pte["valid"]:
                #It's in the page table and is in physical memory currently
                frame_id = pte["frame"]
                frame = frames[frame_id]
                frame["ref"] = True
                frame["last_used"] = access_time
            else:
                #It's not in the page table, and there was no free frame (determined earlier)
                stats["page_faults"] += 1
                stats["disk_accesses"] += 1
                victim_func(pte)


            access_time+= 1

#This loop calls the above function once per algorithm, then resets the frame etc.
for i in alg_list:
    algorithm_loop(i)
    reset_state()
