#!/bin/bash
if [ -z "$1" ]; then
    echo "No target directory specified!"
    exit 1
fi

mkdir -p "$1" && cd "$1"

languages=(
    'en'    'https://voice-prod-bundler-ee1969a6ce8178826482b88e843c335139bd3fb4.s3.amazonaws.com/cv-corpus-3/en.tar.gz'
    'ru'    'https://voice-prod-bundler-ee1969a6ce8178826482b88e843c335139bd3fb4.s3.amazonaws.com/cv-corpus-3/ru.tar.gz'
)

for (( idx=0 ; idx<${#languages[@]} ; idx+=2 )) ; do

    LANG=${languages[idx]}
    FILE=${languages[idx+1]}

    if [ -d "$LANG" ]; then
        echo Skipping "$LANG" as it already exists
        continue
    fi

    echo Downloading "$FILE" to "$LANG"
    mkdir -p "$LANG" && cd "$LANG"
    
    ZIPPED="$LANG.tar.gz"
    wget -q -O "$ZIPPED" "$FILE"  

    echo Extracting "$ZIPPED"

    tar xzf "$ZIPPED"
    ls *.tsv | grep -v ^validated.tsv | xargs rm
    awk -F"\t" '{if ($5 == 0) print $0}' validated.tsv > tmp && mv tmp validated.tsv
    
    awk -F"\t" '{print $2}' validated.tsv > valid_files.txt
    find clips -name "*.mp3" | grep -vFf valid_files.txt | xargs rm -rf
    
    rm valid_files.txt "$ZIPPED"

    #echo Converting "$LANG" to wavs
    sed -i -e 's/\.mp3/\.wav/g' valid_files.txt
    #cd clips
    #find . -type f -name "*.mp3" | while read i; do ffmpeg -loglevel panic -y -i $i $(basename $i).wav; done
    #cd ../

    cd ../
     
done
