####################
# REQUIRED MODULES #
####################

import argparse
from difflib import SequenceMatcher
import pandas as pd
import re
import mwparserfromhell as mwp
import csv
import os
import random

############################
# DECLARE OUTPUT DATAFRAME #
############################

#column_names = ["Title", "Weasel_Sentence", "Updated_Sentence"]
#df = pd.DataFrame(columns = column_names)


###################################################################################################################
# CREATE FUNCTION THAT SPOTS THE DIFFERENCES BETWEEN EACH WEASEL SENTENCE AND ALL SENTENCES OF THE EDITED VERSION #
###################################################################################################################

# THIS WAY WE WILL MANAGE TO FIND THE SENTENCE THAT IS MOST SIMILAR TO THE WEASEL ONE. ALSO STORE THE SIMILARITY PERCENTAGE FOR LATER USE

def spot_sentence(weasel,edited):
    weasel_tag = '[WEASEL]'
    weasel_sentences = []
    edited_sentences = []
    ratios = []
    # To have the correct ratio between weasel and non-weasel sentences, we also add random non-weasel sentences from the original article (So that we have 25% weasel & 75% non-weasel)
    extra_sentences = []
    weasel_indexes = []
    extra_sentences = []

    # Split both versions into sentences.
    tokenized_weasel = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', weasel)
    tokenized_edited = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', edited)

    all_indexes = list(range(0, len(tokenized_weasel)))

    # For the weasel article, extract the specific sentence that contains weasel words #

    ########## ALSO MAKE SURE TO CHECK THE PREVIOUS AND NEXT SENTENCES FOR EACH WEASEL SENTENCE. (match them with the previous and next sentences of the canditate edited sentence) ###########

    for index, item in enumerate(tokenized_weasel):
        if weasel_tag in item:
            # Clean weasel sentences.
            tokenized_weasel_sent = clean_sentence(tokenized_weasel[index])
            weasel_sentences.append(tokenized_weasel_sent)
            weasel_indexes.append(index)

    # Select two random non-weasel sentences.
    non_weasel_indexes = list(set(all_indexes) - set(weasel_indexes) - set([0]))
    random_indexes = random.sample(non_weasel_indexes, 2)
    for i in random_indexes:
        extra_sentences.append(clean_sentence(tokenized_weasel[i]))

    # Compare with edited article #
    for j in range(len(weasel_sentences)):
        max_ratio = 0
        candidate_updated_sentence = None
        for i in range(len(tokenized_edited)):
            # clean candidate updated sentences
            tokenized_edited[i] = clean_sentence(tokenized_edited[i])
            ratio = SequenceMatcher(None, weasel_sentences[j], tokenized_edited[i]).ratio()




            # We choose the sentence of the edited version that has the highest similarity ratio with the weasel sentence.
            if ratio > max_ratio:
                        max_ratio = ratio
                        candidate_updated_sentence = tokenized_edited[i]
            if candidate_updated_sentence == "":
                            candidate_updated_sentence = "NULL"


        edited_sentences.append(candidate_updated_sentence)
        ratios.append(max_ratio)

    return weasel_sentences, edited_sentences, ratios, extra_sentences

##############################################
# CREATE FUNCTION THAT CLEANS THE INPUT TEXT #
##############################################

def clean_text(text):
    weasel_pattern = re.compile(r'((\[|{{)(who|which|by whom|according to whom)(\]|}}|\||\?))|({{weasel(-| )(word|inline))', re.IGNORECASE)

    #### 1. Insert new weasel tag before outdated weasel tag ####
    # In case there are more than one weasel tags, the indexes of the next weasel tags in the text are changed since a new word has been inserted to the text.
    pos = 0
    for match in re.finditer(weasel_pattern, text):
        index = match.start()
        # If the editors put the weasel tag right after a sentence, this means that this particular sentence is the weasel one. So we need to add the new weasel tag to that sentence instead of the next one.
        if text[index + pos - 1] == ".":
            text = text[:index + pos - 1] + ' [WEASEL] ' + text[index - 1 + pos:]
            pos = pos + len(' [WEASEL] ')
        else:
            text = text[:index + pos] + ' [WEASEL] ' + text[index + pos:]
            pos = pos + len(' [WEASEL] ')

    ### 2. Remove . inside all references in each article, so that sentences are not split in the middle due to a reference. Also replace references that don't contain weasels with a specific token. ###
    ref_pattern = re.compile('(?:<\s?ref[^\/ref].*?\/ref\s?>)|(?:<\s?ref name[^>].*?>)')
    # Red pattern also cleans <ref name="name">content</ref> #
    footnote_pattern = re.compile(r'\*.*')


    def clean_references(m):
        ref = m.group(0)
        # If the reference contains the weasel word, then place . in the start and end of this reference (To only capture the reference sentence).
        if '[WEASEL]' in ref:
            clean_ref = ''.join(('.', ref, '.'))
            clean_ref = re.sub(r'(<\s?ref)|(\/ref\s?>)', '', clean_ref)
            return clean_ref
        else:
            clean_ref = '[Reference]'
            return clean_ref

    def clean_footnotes(m):
       footnote = m.group(0)
       clean_footnote = ''.join((footnote, '.'))
       return clean_footnote


    text = ref_pattern.sub(clean_references, text)
    text = footnote_pattern.sub(clean_footnotes, text)


    ### 3. Remove Images ###
    image_pattern = re.compile(r'\[\[Image:.*', re.IGNORECASE)
    text = re.sub(image_pattern, '', text)
    # Gallery tag for multiple images. #
    gallery_tag_pattern = re.compile(r'<\s?gallery\s?>[^<]+(<\s?\/gallery\s?>)', re.IGNORECASE)
    text = re.sub(gallery_tag_pattern, '', text)

    ### To remove footnotes (* ...)
    text = re.sub(r'\*.*', '', text)


    ### 4. Remove Titles ###
    text = re.sub('\=\=.*\=\=', '', text)

    ## 5. Remove Infoboxes ##
    #infobox_pattern = re.compile(r'({{Infobox([^}}]+))|({{Standard table([^{{Close/+/table}}]+){{Close table}})')
    # To remove infobox =, we also must remove each line that starts with |.
    ### To remove lines that start with |
    infobox_pattern = re.compile(r'(^ \ |.* $)|({{Standard table([^{{Close/+/table}}]+){{Close table}})')
    text = re.sub(infobox_pattern, '', text)

    ## 6. Remove Categories ([[Category:XYZ]]) ##
    text = re.sub('\[\[Category:.*\]\]', '', text)

    ## 7. Remove file attachments. For example [[File:Wikipedesketch.png|thumb|alt=A cartoon centipede ... detailed description.|The Wikipede edits ''[[Myriapoda]]''.]] ##

    text = re.sub(r"\[\[File:.*\]\]", "", text)

    ## Add citation tags ##
    text = re.sub(r'{{cite web[^}}]+}}','[Reference]',text)

    ## 8. Clean text with mwp ##
    text = mwp.parse(text).strip_code().strip()


    return text

########################################################
### Prepare function that cleans each result printed. ##
########################################################

def clean_sentence(sent):
    # remove [WEASEL] from weasel sentences
    if '[WEASEL]' in sent:
        sent = re.sub(r'\[WEASEL\]', '', sent)
        # try removing rest weasel tags that could not be removed by mwp.
        temp_pattern = re.compile(r'(\[)(who|which|by whom|according to whom)', re.IGNORECASE)
        sent = re.sub(temp_pattern, '', sent)

    # remove any tags left.
    sent = re.sub(r'<[^>]+>', '', sent)
    # remove any extra spaces.
    sent = " ".join(sent.split())
    # remove unwanted symbols, extra whitespaces, except for letters, numbers, brackets, commas etc
    sent = re.sub('[^A-Za-z0-9()\[\],.% ]+', '', sent)


    return sent




####################################
# DECLARE INPUT & OUTPUT ARGUMENTS #
####################################

# Choose Input.
parser = argparse.ArgumentParser()
# Add input argument.
parser.add_argument("--input", required=True)
# Add output argument.
parser.add_argument("--output", required=True)
# Add 2nd output argument.
parser.add_argument("--extra", required=True)

args = parser.parse_args()

######################
# READ INPUT & PARSE #
######################

raw_data = pd.read_csv(args.input)

#########################################################
### Prepare function that prints results on csv file   ##
#########################################################

def append_content_on_CSV(title, weasel_sentence, edited_sentence, ratio):
    with open(args.output, 'a+') as csv_file:
        # Insert column names into the newly created file.
        if os.stat(args.output).st_size == 0:
            col_names = ['Title', 'Weasel_Sentence', 'Updated_Sentence', 'Similarity_Percentage']
            writer = csv.DictWriter(csv_file, fieldnames=col_names)
            writer.writeheader()
            writer.writerow({'Title': title, 'Weasel_Sentence': weasel_sentence, 'Updated_Sentence': edited_sentence, 'Similarity_Percentage': ratio})
        else:
            col_names = ['Title', 'Weasel_Sentence', 'Updated_Sentence', 'Similarity_Percentage']
            writer = csv.DictWriter(csv_file, fieldnames=col_names)
            writer.writerow({'Title': title, 'Weasel_Sentence': weasel_sentence, 'Updated_Sentence': edited_sentence, 'Similarity_Percentage': ratio})

def append_extra_sentences_on_2nd_csv(title, extra_sentences):
    with open(args.extra, 'a+') as csv_file:
        # Insert column names into the newly created file.
        if os.stat(args.extra).st_size == 0:
            col_names = ['Title', 'Non_Weasel_Sentence']
            writer = csv.DictWriter(csv_file, fieldnames=col_names)
            writer.writeheader()
            for sent in extra_sentences:
                writer.writerow({'Title': title, 'Non_Weasel_Sentence': sent})
        else:
            col_names = ['Title', 'Non_Weasel_Sentence']
            writer = csv.DictWriter(csv_file, fieldnames=col_names)
            for sent in extra_sentences:
                writer.writerow({'Title': title, 'Non_Weasel_Sentence': sent})


### append rows to csv file.
for index, row in raw_data.iterrows():

    title = str(row['Title'])
    weasel = str(row['Weasel_Text'])
    edited = str(row['Edited_Text'])

    weasel_text = clean_text(weasel)
    edited_text = clean_text(edited)

    try:
        weasel_sentences, edited_sentences, ratios, extra_sentences = spot_sentence(weasel_text, edited_text)
    except:
        continue


    for i in range(len(weasel_sentences)):
        weasel_sentence = str(weasel_sentences[i])
        edited_sentence = str(edited_sentences[i])
        # Clean sentences.
        #weasel_sentence = clean_sentence(weasel_sentence)
        #edited_sentence = clean_sentence(edited_sentence)
        ratio = round(ratios[i],2)
        append_content_on_CSV(title, weasel_sentence, edited_sentence, ratio)
        # Add extra non-weasel sentences.
        append_extra_sentences_on_2nd_csv(title, extra_sentences)




# Create a Pandas Excel writer using XlsxWriter as the engine.
#writer = pd.ExcelWriter('dataset.xlsx', engine='xlsxwriter')

# Convert the dataframe to an XlsxWriter Excel object.
#df.to_excel(writer, sheet_name='Sheet1', index = False, header=True)

# Close the Pandas Excel writer and output the Excel file.
#writer.save()

###############################
# STORE SENTENCES TO CSV FILE #
###############################


#df.to_csv (args.output, index = False, header=True)

