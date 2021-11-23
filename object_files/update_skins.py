#https://leagueoflegends.fandom.com/wiki/Champion_skin/All_skins
from bs4 import BeautifulSoup
import requests
import os
import json

#SKIN OBJECT GENERATOR BELOW

page = requests.get("https://leagueoflegends.fandom.com/wiki/Champion_skin/All_skins")
soup = BeautifulSoup(page.content, "html.parser")
folder = "C:/Users/EnderFlop/Desktop/filter test/"

full_names = []
skin_line = []
champ_name = []
for skin in soup.find_all("td", class_="skin-icon"):
  #print(skin.attrs)
  full_names.append(skin.get_text())
  skin_line.append(skin.get("data-skin"))
  champ_name.append(skin.get("data-champion"))

def fix_skin_name(skin_name):
  # This function takes the name of the skin and removes broken characters
  # Such as (:) in the project skins and (/) in the K/DA skins
  skin_name = skin_name.replace(":", "")
  skin_name = skin_name.replace("/", "")
  return skin_name

data = {}

for i in range(len(full_names)): #For each skin
  parsed_skin_name = fix_skin_name(full_names[i]) #Get a fixed version of the title
  data[parsed_skin_name] = {
    "full_name": full_names[i],
    "skin_line": skin_line[i],
    "champion_name": champ_name[i],
  }

with open("object_files/skin_objects.json", "w") as json_file:
  json.dump(data, json_file, indent=4)

#HYPERLINK GENERATOR BELOW

all_links = {}
champion_name = None
#Some skins feature multiple people or are broken. They are added to this list, taking them out of the skins pool
banned_skins_list = [
  "Unmasked Kayle",
]

for title, obj in data.items():

  if title in banned_skins_list:
    continue

  if obj["champion_name"] != champion_name: #If the current skin in the same champ as the last skin, don't get a new request
    champion_name = obj["champion_name"]
    cosmetics = requests.get(f"https://leagueoflegends.fandom.com/wiki/{champion_name}/LoL/Cosmetics")
    #print(f"New Request, {champion_name}")

  soup = BeautifulSoup(cosmetics.content, "html.parser")
  #print(title)
  skin = soup.find("div", attrs={"class":"skin-icon", "data-skin":obj['skin_line']})

  if not skin: #If nothing was found
    print(f"{title} not found")
    continue
  all_links[title] = skin.a.get("href")

with open("object_files/hyperlinks.json", "w") as hyperlinks:
  json.dump(all_links, hyperlinks, indent=4)

print(f"There are {len(data)} skin objects")
print(f"There are {len(all_links)} hyperlinks")