####################
# REQUIRED MODULES #
####################

import xml.sax.handler
import sys
import re
import csv
import os
import argparse

###########################
# DECLARE OUTPUT ARGUMENT #
###########################

parser = argparse.ArgumentParser()
# Add output argument.
parser.add_argument("--output", required=True)
args = parser.parse_args()

#####################################################################################
# CREATE OUTPUT CSV AND APPEND THE INFORMATION THAT WE NEED FOR EACH WEASEL ARTICLE #
#####################################################################################

def append_content_on_CSV(title, weasel_timestamp, weasel, edited_timestamp, edited):
    with open(args.output, 'a+') as csv_file:
        # Insert column names into the newly created file.
        if os.stat(args.output).st_size == 0:
            col_names = ['Title', 'Weasel_Timestamp', 'Weasel_Text', 'Edited_Timestamp', 'Edited_Text']
            writer = csv.DictWriter(csv_file, fieldnames=col_names)
            writer.writeheader()
            writer.writerow({'Title': title, 'Weasel_Timestamp': weasel_timestamp, 'Weasel_Text': weasel,
                             'Edited_Timestamp': edited_timestamp, 'Edited_Text': edited})
        else:
            col_names = ['Title', 'Weasel_Timestamp', 'Weasel_Text', 'Edited_Timestamp', 'Edited_Text']
            writer = csv.DictWriter(csv_file, fieldnames=col_names)
            writer.writerow({'Title': title, 'Weasel_Timestamp': weasel_timestamp, 'Weasel_Text': weasel, 'Edited_Timestamp': edited_timestamp, 'Edited_Text': edited})


##############
# SAX PARSER #
##############

class WikiXMLHandler(xml.sax.handler.ContentHandler):

    def __init__(self):
        super().__init__()
        self.in_title = None
        self.title_content = None
        self.in_page_content = None
        self.page_content = None
        self.in_timestamp = None
        self.timestamp_content = None

        # Temporary parameters
        self.weasel = None
        self.tokenized_weasel = None


        self.weasel_page_already_read = False
        self.edited_page_already_read = False

        # DECLARE THE LIST OF WEASEL TAGS TO SEARCH FOR! #
        self.weasel_pattern = re.compile(r'((\[|{{)(according to whom|which|who|by whom)(\]|}}|\||\?))|({{weasel(-| )(word|inline))', re.IGNORECASE)
        # DECLARE A LIST OF TAGS THAT THE CORRECTED VERSION SHOULD NOT HAVE!
        #self.not_edited_pattern = re.compile(r'((\[|{)(who|which|by whom|according to whom))|({{weasel)',re.IGNORECASE)

        self.not_edited_pattern = re.compile(r'((\[|{{).*(who|whom|which)(\]|}}|\||\?))|({{weasel(-| )(word|inline))', re.IGNORECASE)

        # ARTICLES WITH TITLES THAT CONTAIN User Talk:, User:, Wikipedia:, Talk:,.... WILL NOT BE STORED.
        self.not_wiki_articles = re.compile(r'(User|Talk|Wikipedia).*:', re.IGNORECASE)
        self.in_wiki_article = None

        # Store weasel article title, text and edited text and timestamp
        self.title = None
        self.final_weasel = None
        self.first_edited = None
        self.timestamp = None
        self.weasel_timestamp = None
        self.edited_timestamp = None





    def characters(self, content):

        if self.in_title:
            self.title_content.append(content)

        elif self.in_page_content:
            self.page_content.append(content)

        elif self.in_timestamp:
            self.timestamp_content.append(content)

    def startElement(self, name, attrs):

        if name == 'title':
            self.in_title = True
            self.title_content = []

        elif name == 'text':
            self.in_page_content = True
            self.page_content = []

        elif name == 'timestamp':
            self.in_timestamp= True
            self.timestamp_content = []

    def endElement(self, name):

        if name == 'title':
            self.title = ' '.join(self.title_content)
            self.in_title = False

            # Re-initialize the parameter values to start again with EACH DIFFERENT article.
            self.weasel = None
            self.tokenized_weasel = None
            self.weasel_page_already_read = False
            self.edited_page_already_read = False

            # Check if article is a wiki article.
            if self.not_wiki_articles.search(self.title) is None:
                self.in_wiki_article = True
            else:
                self.in_wiki_article = False

        elif name == 'timestamp' and self.in_wiki_article == True:
            self.timestamp = ' '.join(self.timestamp_content)
            self.in_timestamp = False

        elif name == 'text' and self.in_wiki_article == True:
            Pg_content = ' '.join(self.page_content)
            self.in_page_content = False
            # Was the article in previous versions weasel ?

            ## If article had previous weasel versions but the parser hasn't reached the corrected version yet, keep searching!
            if self.weasel_page_already_read is True and self.edited_page_already_read is False:

                # check if any weasel tag is in current version of article
                if self.weasel_pattern.search(Pg_content) is not None:
                    self.weasel = Pg_content
                    self.weasel_timestamp = self.timestamp
                    self.tokenized_weasel = self.page_content

                # If parser found the first corrected article after a series of weasel articles, STORE THE CORRECTED (updated) ARTICLE and its previous version.
                elif self.not_edited_pattern.search(Pg_content) is None and self.page_content is not None :

                    ##########################
                    # DEALING WITH VANDALISM #
                    ##########################


                    # Check if the number of all sentences of the article is somewhat similar to the number of sentences of the weasel article. (above half the number)

                    if (len(self.page_content) >= len(self.tokenized_weasel) / 2):
                        self.edited_page_already_read = True

                        # Store the versions that we want.
                        self.final_weasel = self.weasel
                        self.edited_timestamp = self.timestamp
                        self.first_edited = Pg_content


            ## If the article had not any weasel versions before, check if its current version is weasel.
            elif self.weasel_page_already_read is False:
                # Check if current version is weasel.
                if self.weasel_pattern.search(Pg_content) is not None:
                    self.weasel = Pg_content
                    self.weasel_timestamp = self.timestamp
                    self.tokenized_weasel = self.page_content
                    self.weasel_page_already_read = True


        # Store to csv output.
        if self.title is not None and self.final_weasel is not None and self.first_edited is not None and self.weasel_timestamp is not None and self.edited_timestamp is not None:
            append_content_on_CSV(self.title, self.weasel_timestamp, self.final_weasel, self.edited_timestamp, self.first_edited)

            # re-declare temporary parameters.
            self.title = None
            self.final_weasel = None
            self.first_edited = None
            self.weasel_timestamp = None
            self.edited_timestamp = None




handler = WikiXMLHandler()

parser = xml.sax.make_parser()
parser.setContentHandler(handler)

for line in sys.stdin:
    parser.feed(line)