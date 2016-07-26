#!/bin/sh
python3 run.py buildmap --no-state-name --stopwords=%stoplists/abbrs.txt,%stoplists/twitter.txt,rt,state,new --workers=16 "$@"
