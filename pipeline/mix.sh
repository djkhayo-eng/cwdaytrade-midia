#!/bin/bash
# Uso: bash mix.sh <voz_raw.mp3> <DUR_segundos>   (no diretório de trabalho com music.wav e sfx.wav gerados por music_sfx.py)
# Voz acelerada 1.15x, começa em 0.1s; trilha com ducking; loudness -14 LUFS.
set -e
ffmpeg -v error -y -i "$1" -af "atempo=1.15,adelay=100|100,highpass=f=80,equalizer=f=3200:t=q:w=1.2:g=2.5,acompressor=threshold=-20dB:ratio=3:attack=5:release=120:makeup=2,alimiter=limit=0.9,apad" -t "$2" -ar 44100 -ac 2 voz.wav
ffmpeg -v error -y -i voz.wav -i music.wav -i sfx.wav -filter_complex "[1:a]volume=0.2[m];[m][0:a]sidechaincompress=threshold=0.02:ratio=5:attack=15:release=400[md];[2:a]volume=0.5[s];[0:a][md][s]amix=inputs=3:normalize=0:duration=first,loudnorm=I=-14:TP=-1.2:LRA=9[o]" -map "[o]" -ar 48000 mix.wav
echo "mix.wav pronto"
