import os
import discord
import random
import asyncio
import math
import json
from async_timeout import timeout
from discord.ext import tasks, commands
from discord.utils import find
from dotenv import load_dotenv
load_dotenv()

REAL_TOKEN = os.getenv("REAL_BOT_TOKEN")
DEV_TOKEN = os.getenv("DEV_BOT_TOKEN")

TOKEN = REAL_TOKEN

bot = commands.Bot(command_prefix=".")
minutes = 3 #Change how often the bot spawns splashes

#STARTUP DIALOGUE AND PRESENCE CHANGE
@bot.event 
async def on_ready():
    print('Logged in as:\n{0.user.name}\n{0.user.id}'.format(bot))
    print("\nGuilds")
    for guild in bot.guilds:
        print(f"{guild.name} (id: {guild.id})")
    print(f"Collect League is in {len(bot.guilds)} servers!")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=f"pic every {minutes} min"))

#COLLECT LEAGUE BOT
class Waifu(commands.Cog):
    def __init__(self, bot, minutes):
        self.bot = bot
        self.color = 0xBB36C9
        self.json_file = "user_data.json"
        self.timeout = 120 #In seconds
        self.main.start()
    
    def cog_unload(self):
        self.main.cancel()

    #SPAWNS CHAMPIONS AND DETECTS CAPTURES
    @tasks.loop(minutes=minutes)
    async def main(self):
        await asyncio.gather(*[self.waifu(guild) for guild in bot.guilds])

    async def waifu(self, guild):
        if await self.check_permissions(guild):
            try:
                game_channel = bot.get_channel(self.server_properties[str(guild.id)]["channel"])
                if game_channel == None: #If the bot couldn't find the game channel, just stop.
                    print(f"Couldn't find the game channel in guild {guild}.")
                    return
            except KeyError:
                print(f"Key Errpr {guild.id} in guild {guild}")
                return

            image_string = random.choice(list(self.hyperlinks))
            link = self.hyperlinks[image_string]
            print(f"Sending {image_string} to {guild.name}")
            parsed_image_string = self.parse_string(image_string)

            champion_embed = discord.Embed(title="A random champion has appeared!", color=self.color)
            champion_embed.set_image(url=link)
            
            await self.send_embed(channel=game_channel, embed=champion_embed)

            try:
                msg = await bot.wait_for("message", check=lambda message: self.champion_check(message, parsed_image_string, game_channel), timeout=self.timeout)
                print(f"{msg.author.name} captured {image_string} in server {msg.guild.name}!")
                self.give_champ(msg, image_string)
                await game_channel.send(embed=discord.Embed(title=f"{msg.author.name} captured {image_string}!", color=self.color))
            except asyncio.TimeoutError:
                print("Timeout")
                await self.send_embed(channel = game_channel, embed=discord.Embed(title=f"{image_string} got away...", color=self.color))
        else:
            print(f"Permission check failed for guild {guild.name}")
    
    #STARTS BOT AND GETS CHANNEL/USER DATA
    @main.before_loop
    async def before_waifu(self):
        print("waifu: waiting for bot to start")
        await bot.wait_until_ready()
        print("waifu: bot online")

        with open("object_files/skin_objects.json") as skin_objects:
            self.skin_objects = json.loads(skin_objects.read())
        with open("object_files/hyperlinks.json") as hyperlinks:
            self.hyperlinks = json.loads(hyperlinks.read())
        with open("object_files/server_properties.json") as server_properties:
            self.server_properties = json.loads(server_properties.read())
        
        for guild in bot.guilds:
            if str(guild.id) not in self.server_properties:
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).send_messages:
                        await self.create_server(channel)
                        break

    #MESSAGE WHEN BOT JOINS NEW SERVER
    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        print(f"Just added to guild {guild.name}!")
        if await self.check_permissions(guild):
            for channel in guild.text_channels:
                #print(f"Checking channel {channel.name}")
                if channel.permissions_for(guild.me).send_messages:
                    await self.create_server(channel)
                    break
        else:
            print(f"Missing permissions in every channel in {guild.name}")

    #ATTEMPTS TO GIVE CHAMPION TO WHOEVER GOT IT
    def give_champ(self, message, champion):
        author = message.author
        user_id = str(author.id)
        user_data = self.get_user_data()
        try:
            if champion in user_data[str(user_id)]["champions"]: 
                user_data[str(user_id)]["champions"][champion]["number_owned"] += 1
            else:
                user_data[str(user_id)]["champions"][champion] = {
                    "number_owned" : 1,
                    }
            user_data[str(user_id)]["number_of_champions"] += 1
            with open(self.json_file, "w") as waifu_data:
                json.dump(user_data, waifu_data, indent=4)
        except KeyError:
            print(f"Creating new user {user_id} ({author.name}).")
            self.create_user(message)
            self.give_champ(message, champion)
    
    #CREATES USER IF NOT IN DATA FILE
    def create_user(self, message):
        author = message.author
        user_id = str(author.id)
        user_data = self.get_user_data()
        try:
            print(f"{user_data[user_id]} exists!") #If you can print this, then the user exists. Should never happen.
        except KeyError:
            user_data[user_id] = {
                "name": author.name,
                "number_of_champions": 0,
                "favorite_champion": None,
                "champions": {},
            }
            with open(self.json_file, "w") as waifu_data:
                json.dump(user_data, waifu_data, indent=4)
    
    async def create_server(self, channel):
        guild = channel.guild
        print(f"Creating properties for guild {guild}")
        self.server_properties[str(guild.id)] = {}
        self.server_properties[str(guild.id)]["server"] = guild.name
        self.server_properties[str(guild.id)]["channel"] = None
        self.server_properties[str(guild.id)]["channel_name"] = None
        self.server_properties[str(guild.id)]["minutes"] = 3
        with open("object_files/server_properties.json", "w") as server_properties:
            json.dump(self.server_properties, server_properties, indent=4)
            print("Properties created and successfully dumped.")

    #DISPLAYS EMBED OF ALL SKINS
    @commands.command(command="skins")
    async def skins(self, ctx):
        user_id = await self.get_user_id(ctx)
        skins_dict = {}
        user_data = self.get_user_data()
        if user_id in user_data.keys():
            for champion in user_data[user_id]["champions"]:
                champion_object = self.skin_objects.get(champion)
                skin_line = champion_object["skin_line"]
                if skin_line in skins_dict.keys():
                    skins_dict[skin_line] += 1
                else:
                    skins_dict[skin_line] = 1
            skins_dict = {k: v for k, v in sorted(skins_dict.items(), key=lambda item: item[0])} #Alphabetizes it
            skins_dict = {k: v for k, v in sorted(skins_dict.items(), key=lambda item: item[1], reverse=True)}
            skins_list = []
            for key, value in skins_dict.items():
                if value > 1:
                    s = "s"
                else:
                    s = "" 
                skins_list.append(f"{key}: {value} skin{s}")
            await self.sendlist(ctx, skins_list, 20, "Skin Lines", user_id)
        elif user_id == None:
            print("User not found.")
        else:
            await self.send_embed(channel=ctx, embed=discord.Embed(title="You have no champions yet!", color=self.color))

    #DISPLAYS EMBED OF ALL CHAMPS
    @commands.command(command="champs")
    async def champs(self, ctx):
        user_id = await self.get_user_id(ctx)
        champs_dict = {}
        user_data = self.get_user_data()
        if user_id in user_data.keys():
            for champion in user_data[user_id]["champions"]:
                champion_object = self.skin_objects.get(champion)
                champion_name = champion_object["champion_name"]
                if champion_name in champs_dict.keys():
                    champs_dict[champion_name] += 1
                else:
                    champs_dict[champion_name] = 1
            champs_dict = {k: v for k, v in sorted(champs_dict.items(), key=lambda item: item[0])} #Alphabetizes it
            champs_dict = {k: v for k, v in sorted(champs_dict.items(), key=lambda item: item[1], reverse=True)} #Orderes it by number collected
            champs_list = []
            for key, value in champs_dict.items():
                if value > 1:
                    s = "s"
                else:
                    s = ""
                champs_list.append(f"{key}: {value} skin{s}")
            await self.sendlist(ctx, champs_list, 20, "Champs List", user_id)
        elif user_id == None:
            print("User not found.")
        else:
            await self.send_embed(channel=ctx, embed=discord.Embed(title="You have no champions yet!", color=self.color))

    #DISPLAYS TOP USERS
    @commands.command(command="top")
    async def top(self, ctx):
        user_data = self.get_user_data()
        users_dict = {}
        for user in user_data:
            name = user_data[user]["name"]
            champ_num = user_data[user]["number_of_champions"]
            users_dict[name] = champ_num
        users_dict = {k: v for k, v in sorted(users_dict.items(), key=lambda item: item[1], reverse=True)}
        users_list = []
        for key, value in users_dict.items():
            users_list.append(f"{key}: {value} skins")
        await self.sendlist(ctx, users_list, 20, "Top Users", ctx.message.author.id)
    
    #DISPLAYS LIST OF CHAMPIONS
    @commands.command(command="list")
    async def list(self, ctx):
        user_id = await self.get_user_id(ctx)
        list_dict = {}
        user_data = self.get_user_data()
        if user_id in user_data.keys():
            for champion in user_data[user_id]["champions"]:
                champion_object = self.skin_objects.get(champion)
                skin_name = champion_object["full_name"]
                number_owned = user_data[user_id]['champions'][champion]['number_owned']
                list_dict[skin_name] = number_owned
            list_dict = {k: v for k, v in sorted(list_dict.items(), key=lambda item: item[1], reverse=True)}
            champ_list = []
            for k, v in list_dict.items():
                if v > 1:
                    copies = ": " + str(v)+ " copies"
                else:
                    copies = ""
                champ_list.append(f"{k}{copies}")
            await self.sendlist(ctx, champ_list, 20, "Skins List", user_id)
        elif user_id == None:
            print("User not found.")
        else:
            await self.send_embed(channel=ctx, embed=discord.Embed(title="You have no champions yet!", color=self.color))
    
    # #UNFINISHED FAVORITE COMMAND
    # @commands.command(command="setfavorite")
    # async def setfavorite(self, ctx):
    #     user_id = ctx.message.author.id
    #     args = self.get_args(ctx.message.content)

    #SEND EMBED OF WHATEVER LIST GIVEN
    async def sendlist(self, ctx, my_list, num_on_page, title, user_id): #Takes a list and sets up logic for a interactive text box of sorts using reactions
        number_of_pages = math.ceil(len(my_list) / num_on_page) #EG 3 pages for 60 lines / 25 on a page 
        list_of_lists = []
        for _ in range(number_of_pages):
            temp_list = []
            for __ in range(num_on_page):
                if my_list: #If there are still elements in the list:
                    temp_list.append(my_list.pop(0)) #Removes first item in the list and adds it to the temp list
            list_of_lists.append(temp_list) #Adds the temp list to the main list of lists
        #We now have a list of lists, each the size of num_on_page
        timeout = True
        page = 0
        message = await self.send_embed(channel=ctx, embed=self.create_embed(list_of_lists[page], title, page+1, number_of_pages, user_id)) #Create embed image
        while timeout == True:      
            if page != 0:
                await message.add_reaction("⬅️")
            if page != number_of_pages - 1:
                await message.add_reaction("➡️")
            try:
                #Wait for a reaction. If the reaction is one of the arrows, move the page. User who adds the reaction must not be a bot. Times out after 60 seconds.
                reaction, _ = await bot.wait_for("reaction_add", check=lambda reaction, user: (str(reaction) == "⬅️" or str(reaction) == "➡️") and not user.bot and reaction.message.id == message.id, timeout=60)
            except asyncio.TimeoutError:
                timeout = False
                await message.clear_reactions()
                break
            if reaction.emoji == "⬅️":
                page -= 1
            elif reaction.emoji == "➡️":
                page += 1
            await message.clear_reactions()
            await message.edit(embed=self.create_embed(list_of_lists[page], title, page+1, number_of_pages, user_id)) #Edit embed image with new page and data

    #CREATES EMBED FOR sendlist
    def create_embed(self, my_list, title, current_page, max_pages, user_id): #Takes a list and a title and returns an embed where each line is a value in that list.
        string = ""
        for i in range(len(my_list)):
            string += my_list[i] + "\n"
        string += f"\nPage {current_page} of {max_pages}"
        embed = discord.Embed(title=title, color=self.color)
        embed.set_author(name=bot.get_user(int(user_id)))
        embed.add_field(name="--------------", value=string, inline=False)
        return embed

    #MODIFIES STRING TO MAKE THINGS FRIENDLIER
    def parse_string(self, string):
        string = string.lower() #lowercase  
        string = string.replace(" ", "") #removes spaces
        string = string.replace("original", "") #removes original (original zyra)
        string = string.replace("'", "") #removes apostrophe (kai'sa, kha'zix)
        string = string.replace("-", "") #removes dashes (almost-prom king amumu)
        string = string.replace(".", "") #removes periods (mr. mundoverse)
        string = string.replace(":", "") #removes colons (PROJECT: Pyke)
        string = string.replace("/", "") #removes slashes (K/DA)
        string = string.replace(",", "") #removes commas (Gragas, Esq.)
        string = string.replace("&willump", "") #removes &willump (demolisher nunu & willump)
        return string

    #Get list of string args after a command
    def get_args(self, string):
        string_list = [string]
        split_list = string_list[0].split()
        #print(f"arguments = {split_list[1:]}")
        return split_list[1:] #returns a list of string arguments, minus the command.

    #Discord @ comes with bloat. This removes that. Returns a string
    def format_at(self, arg):
        arg = arg.replace("<","")
        arg = arg.replace(">","")
        arg = arg.replace("@","")
        arg = arg.replace("!","")
        return arg

    #Takes context, returns @'d user if user @'d, else returns user. Returns None if not correct @ or user. RETURNS A STRING
    async def get_user_id(self, ctx): 
        args = self.get_args(ctx.message.content)
        if args:
            user_id = self.format_at(args[0])
            try:
                if bot.get_user(int(user_id)) != None:
                    return user_id
                else:
                    print("User not found. Argument probably wasn't an @.")
                    await self.send_embed(channel=ctx, embed=discord.Embed(title="User not found. Did you @ a user?", color=self.color))
                    return None
            except ValueError:
                print("User not found. Argument probably wasn't an @.")
                await self.send_embed(channel=ctx, embed=discord.Embed(title="User not found. Did you @ a user?", color=self.color))
                return None
        else:
            return str(ctx.message.author.id)
    
    def get_user_data(self):
        with open(self.json_file) as waifu_data:
            user_data = json.load(waifu_data)
        return user_data
    
    @commands.command(command="setchannel")
    @commands.has_permissions(manage_channels=True)
    async def setchannel(self, ctx):
        self.server_properties[str(ctx.guild.id)]["channel"] = ctx.channel.id
        self.server_properties[str(ctx.guild.id)]["channel_name"] = ctx.channel.name
        with open("object_files/server_properties.json", "w") as server_properties:
            json.dump(self.server_properties, server_properties, indent=4)
        await self.send_embed(channel=ctx, embed=discord.Embed(title=f"Collect League will now send splash arts to {ctx.channel.name}.", color=self.color))
    
    @setchannel.error
    async def setchannel_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await self.send_embed(channel=ctx, embed=discord.Embed(title="You need Manage Channels permissions to do that.", color=self.color))

    # @commands.command(command="setminutes")
    # @commands.has_permissions(manage_channels=True)
    # async def setminutes(self, ctx):
    #     ctx.send(embed=discord.Embed(title="This doesn't really do anything right now", color=self.color))
    #     args = self.get_args(ctx.message.content)
    #     if args:
    #         try:
    #             minutes = int(args[0])
    #         except ValueError:
    #             await ctx.send(embed=discord.Embed(title="That's not a number...", color=self.color))
    #             return
    #         self.server_properties[str(ctx.guild.id)]["minutes"] = minutes
    #         with open("object_files/server_properties.json", "w") as server_properties:
    #             json.dump(self.server_properties, server_properties, indent=4)
    #     else:
    #         await ctx.send(embed=discord.Embed(title="Use '.setminutes {number}'", color=self.color))

    # @setminutes.error
    # async def setminutes_error(self, ctx, error):
    #     await ctx.send(embed=discord.Embed(title="You need Manage Channels permissions to do that.", color=self.color))

    
    def champion_check(self, message, image_string, channel):
        if self.parse_string(message.content) == image_string and message.channel == channel:
            return True
        return 
        
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if hasattr(ctx.command, "on_error"): #If already being handled
            return
        error = getattr(error, "original", error)
        if isinstance(error, commands.CommandNotFound):
            await self.send_embed(channel=ctx, embed=discord.Embed(title="Command Not Found", color=self.color))
        if isinstance(error, commands.MissingRequiredArgument):
            await self.send_embed(channel=ctx, embed=discord.Embed(title="Missing An Argument", color=self.color))
        if isinstance(error, commands.BotMissingPermissions):
            await self.send_embed(channel=ctx, embed=discord.Embed(title="Missing Permissions.\nMake sure you give the bot all the permissions it asks for when it joins!", color=self.color))
        if isinstance(error, commands.MissingPermissions):
            await self.send_embed(channel=ctx, embed=discord.Embed(title="Missing Permissions.\nMake sure you give the bot all the permissions it asks for when it joins!", color=self.color))

    async def check_permissions(self, guild):
        permissions = guild.me.guild_permissions
        if permissions.add_reactions and permissions.read_messages and permissions.send_messages and permissions.embed_links and permissions.manage_messages:
            return True
        else:
            return False
    
    async def send_embed(self, channel, embed):
        try:
            return await channel.send(embed=embed)
        except (discord.Forbidden, discord.NotFound) as error: #Forbidden stops permissions, NotFound fixes when something happens to the channel after it was found.
            print(f"Error ({error}) when attempting to send embed")
    
bot.add_cog(Waifu(bot, minutes))

bot.run(TOKEN)


#TODO
#Add new features (more organization tools, fight system, favorite champion)
#.prestige, displays all prestige skins
#add champion arg after display commands? ".skins kaisa" displays all your kaisa skins
#Replace get_args with discord arg system. Learn more here
#https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html