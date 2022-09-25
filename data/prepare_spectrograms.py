import sys
import os
import numpy as np
from itertools import groupby
from pathlib import Path
import random


sys.path.insert(0, "../")

from dataset import loaders
from utils import audio
from params.params import Params as hp



def progress(progress, prefix='', length=70):
    """Prints a pretty console progress bar.

    Arguments:
        progress -- percentage (from 0 to 1.0)
    Keyword argumnets:
        prefix (default: '') -- string which is prepended to the progress bar
        length (default: 70) -- size of the full-size bar
    """
    progress *= 100
    step = 100/length
    filled, reminder = int(progress // step), progress % step
    loading_bar = filled * '█'
    loading_bar += '░' if reminder < step / 3 else '▒' if reminder < step * 2/3 else '▓'
    loading_bar += max(0, length - filled) * '░' if progress < 100 else ''
    print(f'\r{prefix} {loading_bar} {progress:.1f}%', end=('' if progress < 100 else '\n'), flush=True)



if __name__ == '__main__':
    import argparse
    import re
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset_directory", type=str, default="my_common_voice", help="Base directory of Common Voice.")
    parser.add_argument("--loader_name", type=str, default="my_common_voice", help="Name of the loader (for the type of the dataset).")
    parser.add_argument("--percent_val_per_speaker", type=str, default="15", help="Percentage of the samples for validation per speaker.")
    parser.add_argument("--sample_rate", type=int, default=22050, help="Sample rate.")
    parser.add_argument("--num_fft", type=int, default=1102, help="Number of FFT frequencies.")
    parser.add_argument("--num_mels", type=int, default=80, help="Number of mel bins.")
    parser.add_argument("--stft_window_ms", type=float, default=50, help="STFT window size.")
    parser.add_argument("--stft_shift_ms", type=float, default=12.5, help="STFT window shift.")
    parser.add_argument("--no_preemphasis", action='store_false', help="Do not use preemphasis.")
    parser.add_argument("--preemphasis", type=float, default=0.97, help="Strength of preemphasis.")

    args = parser.parse_args()

    hp.sample_rate = args.sample_rate
    hp.num_fft = args.num_fft

    train_filepath = os.path.join(args.dataset_directory, "train.txt")
    val_filepath   = os.path.join(args.dataset_directory, "val.txt")
    

    spectrogram_dirs = [os.path.join(args.dataset_directory, 'spectrograms'), 
                        os.path.join(args.dataset_directory, 'linear_spectrograms')
                       ]
    for x in spectrogram_dirs:
        if not os.path.exists(x): os.makedirs(x)
    
    ## Gather the metafiles
    metadata_paths = list(Path(args.dataset_directory).glob("*/meta.csv"))


    print(f'Please wait, this may take a very long time.')

    languages = list(map(lambda metadata_paths: metadata_paths.parent.stem, metadata_paths))
    print("\nLanguages: ", languages, "\n")
    
    ph = ""  # No use of phonemes so far
    idx = 0 # unique index of a spectrogram

    with open(train_filepath, 'w', encoding='utf-8') as f_train:
        with open(val_filepath, 'w', encoding='utf-8') as f_val:

            for lang in range(len(languages)):
                # Load metafiles, separately for each language. An item is a list like: [text, audiopath, speaker_id, language ]
                metadata_items = loaders.get_loader_by_name(args.loader_name)(args.dataset_directory, meta_files=[metadata_paths[lang].as_posix()])

                # Gather each speaker of that language
                speaker_wavs_count = [[speaker, len(list(all_speaker_wavs))] for speaker, all_speaker_wavs in           # Take just the number of audio_paths of the same speaker
                                    groupby(metadata_items, lambda item: item[2])]                                      # group by the speaker (metadata_items[2] is the speaker)

                speaker_processed_so_far = [[speaker, 0] for speaker, count in speaker_wavs_count]
                
                speaker_val_count = [[speaker, max(1, round(count*float(args.percent_val_per_speaker)/100))] for speaker, count in speaker_wavs_count]
                speaker_selected_val_so_far = [[speaker, 0] for speaker, count in speaker_wavs_count]
                
        #        print("\n\nSpeaker_wavs_count:\n", speaker_wavs_count, "\n")
        #        print("\n\nSpeaker_val_count:\n", speaker_val_count, "\n")
        #        print("\n\nSpeaker_selected_val_so_far:\n", speaker_selected_val_so_far, "\n")

                len_m = len(metadata_items)
                for i in range(len_m):
                    raw_text, a_path, speaker_id, language = metadata_items[i]
                    idx_str = str(idx).zfill(6)
                    spec_name =  idx_str + '.npy'      
                    audio_path = os.path.join(args.dataset_directory, a_path)       
                    audio_data = audio.load(audio_path)
                    mel_path_partial = os.path.join("spectrograms", spec_name)
                    lin_path_partial = os.path.join("linear_spectrograms", spec_name)

                    mel_path = os.path.join(args.dataset_directory, mel_path_partial)
                    np.save(mel_path, audio.spectrogram(audio_data, True))
                    lin_path = os.path.join(args.dataset_directory, lin_path_partial)
                    np.save(lin_path, audio.spectrogram(audio_data, False))

                    # Choose where to save: whether in train.txt or in val.txt
                    # find the total number of files of that speaker in selected_val_so_far
                    for spk_ix in range(len(speaker_wavs_count)):
                        if speaker_wavs_count[spk_ix][0] == speaker_id:
                            speaker_index = spk_ix
                            break

                    this_speaker_total_count = speaker_wavs_count[speaker_index][1]
                    this_speaker_processed_so_far = speaker_processed_so_far[speaker_index][1]
                    this_speaker_val_count = speaker_val_count[speaker_index][1]
                    this_speaker_val_count_so_far = speaker_selected_val_so_far[speaker_index][1]

#                    print("For speaker ", speaker_id, " total number of wavs = ", this_speaker_total_count, " val = ", this_speaker_val_count, " so far = ", this_speaker_val_count_so_far)

                    if (this_speaker_val_count_so_far < this_speaker_val_count):

                        if ((this_speaker_total_count - this_speaker_processed_so_far) <= (this_speaker_val_count - this_speaker_val_count_so_far)):
                            some_criteria = False   # There is no more randomness, select all to the end for validation
                        else:
                            if (random.randint(0,100) < int(args.percent_val_per_speaker)):
                                some_criteria = False    # include in the val
                            else:
                                some_criteria = True     # include in the train
                    else: some_criteria = True # val.txt already filled enough with this speaker

                    if (some_criteria):
                        f = f_train
                    else:
                        f = f_val
                        # update the val_count_so_far for this speaker
                        this_speaker_val_count_so_far = this_speaker_val_count_so_far + 1
                        speaker_selected_val_so_far[speaker_index][1] = this_speaker_val_count_so_far

                    speaker_processed_so_far[speaker_index][1] = speaker_processed_so_far[speaker_index][1] + 1

                    print(f'{idx_str}|{speaker_id}|{language}|{a_path}|{mel_path_partial}|{lin_path_partial}|{raw_text}|{ph}', file=f)
                    
                    progress((i + 1) / len_m, prefix='Building metafile for: ' + language + " ")
                    idx += 1

        f_val.close()
    f_train.close()