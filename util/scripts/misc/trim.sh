#!/bin/sh

for i in {00..36}
do
    cat songs${i}.json | cut -d ":" -f 2 | cut -d "," -f 1 | tr -d \" | tr -d " " > ids${i}.txt
done
