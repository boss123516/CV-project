#!/usr/bin/env python3
"""Offline Korean speech using the existing system libespeak-ng."""
import ctypes as C
from pathlib import Path
import subprocess
import sys
import wave


def synthesize(text, path):
    lib=C.CDLL('libespeak-ng.so.1')
    lib.espeak_Initialize.argtypes=[C.c_int,C.c_int,C.c_char_p,C.c_int]
    rate=lib.espeak_Initialize(2,0,None,0)
    if rate<=0: raise RuntimeError('espeak-ng initialization failed')
    lib.espeak_SetVoiceByName.argtypes=[C.c_char_p]
    if lib.espeak_SetVoiceByName(b'ko')!=0: raise RuntimeError('Korean voice not installed')
    lib.espeak_SetParameter(1,160,0)
    chunks=[]
    CALLBACK=C.CFUNCTYPE(C.c_int,C.POINTER(C.c_short),C.c_int,C.c_void_p)
    @CALLBACK
    def callback(samples,count,events):
        if samples and count>0: chunks.append(C.string_at(samples,count*2))
        return 0
    lib.espeak_SetSynthCallback(callback)
    lib.espeak_Synth.argtypes=[C.c_void_p,C.c_size_t,C.c_uint,C.c_int,C.c_uint,C.c_uint,C.c_void_p,C.c_void_p]
    encoded=text.encode('utf-8')+b'\0'
    result=lib.espeak_Synth(encoded,len(encoded),0,1,0,1,None,None)
    if result!=0: raise RuntimeError(f'espeak synthesis failed: {result}')
    lib.espeak_Synchronize()
    with wave.open(str(path),'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(rate); f.writeframes(b''.join(chunks))
    lib.espeak_Terminate()


if __name__=='__main__':
    target=Path(sys.argv[2])
    synthesize(sys.argv[1],target)
    if '--play' in sys.argv[3:]: subprocess.run(['paplay',str(target)],check=True)
