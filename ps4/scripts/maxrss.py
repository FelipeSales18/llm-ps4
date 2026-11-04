#!/usr/bin/env python3
"""Substituto de `/usr/bin/time -v` (ausente no PS4): roda o comando, repassa
stdout/stderr e imprime em stderr o pico de RSS (ru_maxrss dos filhos, em kB) e o tempo."""
import resource, subprocess, sys, time
t0 = time.time()
rc = subprocess.call(sys.argv[1:])
ru = resource.getrusage(resource.RUSAGE_CHILDREN)
sys.stderr.write(f"\n\tMaximum resident set size (kbytes): {ru.ru_maxrss}\n"
                 f"\tElapsed (wall clock) time (s): {time.time()-t0:.1f}\n"
                 f"\tUser time (s): {ru.ru_utime:.1f}\n\tSystem time (s): {ru.ru_stime:.1f}\n"
                 f"\tExit status: {rc}\n")
sys.exit(rc)
