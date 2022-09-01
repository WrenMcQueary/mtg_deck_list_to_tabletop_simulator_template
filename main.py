"""Takes in a filepath which leads to a folder.  The folder should be empty except for a file called 'decklist.txt'.
Each line of decklist.txt should be a positive integer followed by a tab, followed by the name of a card, followed by
newline.
Produces an image of the deck defined by the list that can be imported into Tabletop Simulator.
"""

import os           # To make output folder(s)
import requests     # To get image from web
import shutil       # To save it locally
from mtgsdk import Card     # Backup option to find a card's image URL.
import scrython     # To find a card's image URL.
from skimage import io, transform  # For image processing.
from pathlib import Path

# TODOs
# TODO: Upscale card_template.png to 6552 pixel rows x 6720 pixel columns, so that scryfall images can be used at full resolution.
# TODO: Allow for image FINDing, template BUILDing, or BOTH.
# TODO: Fall back on mtgsdk when scrython can't find an image.
# TODO: Handle double-sided cards (eg transform).
# TODO: Make a version that repeatedly updates a Google Drive folder and runs on Raspberry Pi.


class Decklist:
    """All the cards in a deck."""

    def __init__(self, entry):
        """entry is a list of 'number\tname\n'"""
        self.list = []
        for item in entry:
            self.list.append(QuantityAndCard(int(item.split("\t")[0]), item.split("\t")[1].replace("\n", "")))


class QuantityAndCard:
    """A quantity paired with a card.
    quantity is an integer.
    card is a string, specifically the full name of the card, including spaces and capitalization.
    """

    def __init__(self, quantity, card):
        self.quantity = quantity
        self.card = card


def get_decklist_object(folder_name):
    """Return a Decklist object for this deck.
    folder_name is a string.
    """
    decklist_filepath = "Decklists/" + folder_name + "/decklist.txt"
    decklist_file = open(decklist_filepath, "r")
    decklist_list = decklist_file.readlines()
    decklist_file.close()
    decklist_object = Decklist(decklist_list)
    return decklist_object


def download_all_images_for_deck(folder_name, decklist):
    """Create a folder called "Decklists/"+folder_name+"/output/card_images" and download all card images in decklist to it.
    folder_name is a string.
    decklist is a Decklist object.
    """
    for quantity_and_card in decklist.list:
        this_card = quantity_and_card.card
        # Get this card's image URL using scryfall.
        if this_card == "Barkchannel Pathway":  # TODO: Remove this filthy quickfix
            this_image_url = "https://c1.scryfall.com/file/scryfall-cards/large/front/b/6/b6de14ae-0132-4261-af00-630bf15918cd.jpg?1615648805"
        elif this_card == "Cragcrown Pathway":
            this_image_url = "https://c1.scryfall.com/file/scryfall-cards/large/front/d/a/da57eb54-5199-4a56-95f7-f6ac432876b1.jpg?1604264349"
        elif this_card == "Hengegate Pathway":
            this_image_url = "https://c1.scryfall.com/file/scryfall-cards/large/front/8/b/8b13ff20-1dad-4c6a-979b-4d2662af5e74.jpg?1610653579"
        elif this_card == "Needleverge Pathway":
            this_image_url = "https://c1.scryfall.com/file/scryfall-cards/large/front/e/d/edc71870-656c-40f9-b2b0-f69a46bf8c51.jpg?1601142287"
        elif this_card == "Riverglide Pathway":
            this_image_url = "https://c1.scryfall.com/file/scryfall-cards/large/front/7/8/78792607-0872-4de4-a9d8-92f1d58f4a71.jpg?1603423755"
        elif this_card == "Tangled Florahedron":
            this_image_url = "https://c1.scryfall.com/file/scryfall-cards/large/front/2/3/235d1ffc-72aa-40a2-95dc-3f6a8d495061.jpg?1604199647"
        else:
            this_image_url = scrython.cards.Named(fuzzy=this_card).scryfallJson["image_uris"]["large"]

        # Download this card from Gatherer using its Multiverse ID.
        r = requests.get(this_image_url, stream=True)
        if r.status_code == 200:
            image_file = open("Decklists/" + folder_name + "/output/card_images/" + this_card.replace("//", " AND ") + ".jpg", "wb")    # Replace // with AND to avoid filepath issues.
            shutil.copyfileobj(r.raw, image_file)
            image_file.close()
        else:
            raise ValueError("Image couldn't be retrieved.")


def assemble_complete_template(folder_name, decklist):
    """Saves a version of the template with all images in decklist attached.
    Exports to "Decklists/"+folder_name+"/output/card_images"
    card_template.png contains 7 rows and 10 columns.
    """

    # Load card_template.png from project folder and process it.
    template_file = io.imread("card_template.png")
    # Remove the alpha layer from template_file.
    template_file = template_file[:, :, 0:3]

    # Set dimensional constants.
    template_card_height_pixels = 580
    template_card_width_pixels = 406

    # Repeatedly load each image, scale it, and attach it to the right spot on the loaded version of card_template.png
    this_row, this_column = 0, 0    # Keeping track of what spot on the template this image should go.
    for this_quantity_and_card in decklist.list:
        for ii in range(this_quantity_and_card.quantity):   # For all instances of this card:
            # Load the image.
            this_card_file = io.imread("Decklists/" + folder_name + "/output/card_images/" + this_quantity_and_card.card.replace("//", " AND ") + ".jpg")   # Replace // with AND to avoid filepath issues.
            # Scale the image.
            rescaled_this_card_file = transform.rescale(this_card_file, (template_card_height_pixels/this_card_file.shape[0], template_card_width_pixels/this_card_file.shape[1], 1))
            # Remove the alpha layer from this image.
            rescaled_this_card_file = rescaled_this_card_file[:, :, 0:3]
            # Scale the levels up from 0-1 to 0-255.
            rescaled_this_card_file = rescaled_this_card_file * 255
            # Place the image at the correct coordinates on template_file.
            template_file[this_row*template_card_height_pixels:this_row*template_card_height_pixels+template_card_height_pixels, this_column*template_card_width_pixels:this_column*template_card_width_pixels+template_card_width_pixels] = rescaled_this_card_file
            # Update coordinates.
            this_column += 1
            if this_column > 9:
                this_row += 1
                this_column = 0
                if (this_column == 9 and this_row == 6) or this_row > 6:
                    raise ValueError("Too many cards in the deck to put on one template.  The limit is 69 cards.")

    # Export!
    io.imsave("Decklists/" + folder_name + "/output/completed_template/completed_template.jpg", template_file)


#
# MAIN SCRIPT
#

# User-set parameters
decklist_folder_name_list = input("Enter the names of folders to create a template image for, separated by tabs: ").split("\t")

print("Working...")
for decklist_folder_name in decklist_folder_name_list:
    # Create the folder structure for output.
    try:
        dir_path = Path("Decklists/" + decklist_folder_name + "/output")
        dir_path.rmdir()
    except FileNotFoundError as err:
        pass
    os.makedirs("Decklists/" + decklist_folder_name + "/output")
    os.makedirs("Decklists/" + decklist_folder_name + "/output/card_images")
    os.makedirs("Decklists/" + decklist_folder_name + "/output/completed_template")

    # Parse the list to a decklist object.
    decklist_object = get_decklist_object(decklist_folder_name)

    # Download all images from gatherer.wizards.com.
    download_all_images_for_deck(decklist_folder_name, decklist_object)

    # Fill in the template and export.
    assemble_complete_template(decklist_folder_name, decklist_object)

    print("Done with " + decklist_folder_name)
print("DONE WITH ALL!")
