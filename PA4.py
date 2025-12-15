from dataclasses import dataclass
from typing import Dict, List
import sys
import math
import time
import random

alg_list = ['RAND', 'FIFO', 'LRU', 'PER', 'oracle']

input_file = sys.argv[1]
random_seed = sys.argv[2]
#algorithm = sys.argv[2]

#define random seed
random.seed(random_seed)

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


def RAND_victim(pte, pid, vpn):
    global stats, frames, access_time, page_table
    #generate a random location between 0 - 31 on physical main memory
    victim_page_RAND = random.randint(0, NUM_FRAMES - 1) 

    #locate pid, vpn to determine which page table the main memory (MM) entry belongs to
    old_pid = frames[victim_page_RAND]['pid']
    old_vpn = frames[victim_page_RAND]['vpn']

    #set entry to not valid - there is not a translation in MM
    page_table[old_pid][old_vpn] = {
        'valid': False,
        'frame': None,
        'dirty': False
    }

    #if physical memory victim has a dirty bit increment dirty writes and disk accesses
    if frames[victim_page_RAND]["dirty"]:
        stats["disk_accesses"] += 1
        stats["dirty_writes"] += 1
    
    #set entry to valid - there is a translation to MM and assign frame index
    pte['valid'] = True
    pte['frame'] = victim_page_RAND

    #update MM to new entry
    frames[victim_page_RAND] = {
        "pid":pid,
        "vpn":vpn,
        "ref": True,
        "dirty":pte['dirty'],
        "load_time": access_time,
        "last_used": access_time
    }
    

def FIFO_victim(pte, pid, vpn):
    oldest_frame = 0
    global stats, frames, access_time, page_table
    #print(frames)
    for i in range(NUM_FRAMES):
        if frames[i]["load_time"] < frames[oldest_frame]["load_time"]:
            oldest_frame = i

    old_pid = frames[oldest_frame]['pid']
    old_vpn = frames[oldest_frame]['vpn']
    old_pte = page_table[old_pid][old_vpn]
    
    old_pte["valid"] = False
    old_pte["frame"] = None

    if frames[oldest_frame]["dirty"]:
        stats["disk_accesses"] += 1
        stats["dirty_writes"] += 1
        old_pte["dirty"] = False

    pte['valid'] = True
    pte['frame'] = oldest_frame

    frames[oldest_frame] = {
        "pid":pid,
        "vpn":vpn,
        "ref": True,
        "dirty":pte['dirty'],
        "load_time": access_time,
        "last_used": access_time

    }


def LRU_victim(pte, pid, vpn):
    pass

def PER_victim(pte, pid, vpn):
    pass

def oracle_victim(pte, pid, vpn):
    pass

victim_dispatch = {
    "RAND": RAND_victim,
    "FIFO":FIFO_victim,
    "LRU":LRU_victim,
    "PER": PER_victim,
    "oracle": oracle_victim
}

victim_func = None


#This loop iterates through the selected file. It is given an algorithm and then processes each memory access one at a time.
def algorithm_loop(algorithm):
    print(f"Running: {algorithm}")
    global stats, victim_func, frames, access_time
    access_time = 0
    victim_func = victim_dispatch[algorithm]
    stats = stats_dispatch[algorithm]
    with open(input_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line: continue

            parts = line.split()
            pid = int(parts[0])
            addr = int(parts[1])
            vpn = addr >> 9
            access = parts[2]
            #print(f"PID: {pid}")
            #print(f"VPN: {vpn}")
           
            '''
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
                    continue
            '''
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

            pte["ref"] = True
            if access == 'W':
                pte['dirty'] = True

            if pte is not None and pte["valid"]:
                #It's in the page table and is in physical memory currently
                frame_id = pte["frame"]
                frames[frame_id]["ref"] = True
                frames[frame_id]["last_used"] = access_time
                if access == "W":
                    frames[frame_id]["dirty"] = True
            else:
                #It's not in the page table
                stats["page_faults"] += 1
                stats["disk_accesses"] += 1

                free_frame = next((i for i in range(NUM_FRAMES) if frames[i] is None), None)

                if free_frame is not None:
                    # load into free frame
                    pte["valid"] = True
                    pte["frame"] = free_frame
                    frames[free_frame] = {
                        "pid": pid,
                        "vpn": vpn,
                        "ref": True,
                        "dirty": (access == "W"),
                        "load_time": access_time,
                        "last_used": access_time,
                    }
                else:
                    victim_func(pte, pid, vpn)


            access_time += 1

#This loop calls the above function once per algorithm, then resets the frame etc.
for i in alg_list:
    algorithm_loop(i)
    reset_state()
    print(stats_dispatch[i])
