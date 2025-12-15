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
access_quantity = 0


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

    #locate pid, vpn to determine which page table the original main memory (MM) entry belongs to
    old_pid = frames[victim_page_RAND]['pid']
    old_vpn = frames[victim_page_RAND]['vpn']
    old_pte = page_table[old_pid][old_vpn]

    #set entry to not valid - there is not a translation in MM
    old_pte["valid"] = False
    old_pte["frame"] = None

    #if physical memory victim has a dirty bit increment dirty writes and disk accesses
    if frames[victim_page_RAND]["dirty"]:
        stats["disk_accesses"] += 1
        stats["dirty_writes"] += 1
        old_pte["dirty"] = False
    
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
    global stats, frames, access_time, page_table

    #Locate Least Recently Used index on MM
    victim_page_LRU = 0
    for i in range(NUM_FRAMES):
         if frames[i]["last_used"] < frames[victim_page_LRU]["last_used"]:
             victim_page_LRU = i

    #locate pid, vpn to determine which page table the original main memory (MM) entry belongs to
    old_pid = frames[victim_page_LRU]['pid']
    old_vpn = frames[victim_page_LRU]['vpn']
    old_pte = page_table[old_pid][old_vpn]

    #set entry to not valid - there is not a translation in MM
    old_pte["valid"] = False
    old_pte["frame"] = None

    #if physical memory victim has a dirty bit increment dirty writes and disk accesses
    if frames[victim_page_LRU]["dirty"]:
        stats["disk_accesses"] += 1
        stats["dirty_writes"] += 1
        old_pte["dirty"] = False
    
    #set entry to valid - there is a translation to MM and assign frame index
    pte['valid'] = True
    pte['frame'] = victim_page_LRU

    #update MM to new entry
    frames[victim_page_LRU] = {
        "pid":pid,
        "vpn":vpn,
        "ref": True,
        "dirty":pte['dirty'],
        "load_time": access_time,
        "last_used": access_time
    }

def PER_victim(pte, pid, vpn):
    global stats, frames, access_time, page_table
    #of note is that the first requirement of PER doesn't require specific implementation here because it happens by default in the main loop as we assumed it would always need to happen regardless of algorithm
    victim_frame = None
    categories = [(0,0), (0,1), (1,0), (1,1)]
    for r, d in categories:
        for i in range(NUM_FRAMES):
            fr = frames[i]
            if fr is None:
                continue
            if int(fr["ref"]) == r and int(fr["dirty"]) == d:
                victim_frame = i
                break
        if victim_frame is not None:
            break

    old_pid = frames[victim_frame]['pid']
    old_vpn = frames[victim_frame]['vpn']
    old_pte = page_table[old_pid][old_vpn]
    
    old_pte["valid"] = False
    old_pte["frame"] = None

    if frames[victim_frame]["dirty"]:
        stats["disk_accesses"] += 1
        stats["dirty_writes"] += 1
        old_pte["dirty"] = False

    pte['valid'] = True
    pte['frame'] = victim_frame

    frames[victim_frame] = {
        "pid":pid,
        "vpn":vpn,
        "ref": 1,
        "dirty":pte['dirty'],
        "load_time": access_time,
        "last_used": access_time

    }



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
    #access_quantity = 0
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

            if algorithm == "PER" and access_time % 200 == 0 and access_time > 0:
                for i in range(NUM_FRAMES):
                    if frames[i] is not None:
                        frames[i]["ref"] = 0

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

            pte["ref"] = 1
            if access == 'W':
                pte['dirty'] = True

            if pte is not None and pte["valid"]:
                #It's in the page table and is in physical memory currently
                frame_id = pte["frame"]
                frames[frame_id]["ref"] = 1
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
                        "ref": 1,
                        "dirty": (access == "W"),
                        "load_time": access_time,
                        "last_used": access_time,
                    }
                else:
                    victim_func(pte, pid, vpn)
                    #access_quantity += 1


            access_time += 1

#This loop calls the above function once per algorithm, then resets the frame etc.
for i in alg_list:
    algorithm_loop(i)
    reset_state()
    print(stats_dispatch[i])
