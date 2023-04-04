import discord, sqlite3, asyncio, datetime


client = discord.Client(intents= discord.Intents.all())

personal_channel_category = 0



def executeDB(query, args = (), commit = False):
    conn= sqlite3.connect("db.db")
    c = conn.cursor()
    res = list(c.execute(query, args))
    if commit: conn.commit()
    conn.close()
    return res
    
@client.event
async def on_ready():
    print(client.user)
    while True:
        now = datetime.datetime.now()
        offset = datetime.datetime.now().weekday()
        now = now - datetime.timedelta(offset)
        if( len(executeDB("SELECT * FROM resetlog WHERE date=?", (f"{now.year}-{now.month}-{now.day}",))) < 1 ):
            executeDB("UPDATE channel set counts=0", commit=True)
            executeDB("INSERT INTO resetlog VALUES(?)", (f"{now.year}-{now.month}-{now.day}",), commit=True)
        await asyncio.sleep(5)



@client.event
async def on_message(message: discord.Message):
    if(message.content.startswith("!setup") and message.author.guild_permissions.administrator):
        await message.delete()
        embed = discord.Embed(title="개인채널 생성", description="개인 채널을 생성하려면 버튼을 눌러주세요.")
        view = discord.ui.View()
        view.add_item(discord.ui.Button(custom_id="create_custom_channel", label="개인 채널 생성", style= discord.ButtonStyle.green))
        await message.channel.send(embed=embed, view=view)

    if( message.channel.type == discord.ChannelType.text and message.channel.category.id == personal_channel_category and not message.author == client.user):
            res = executeDB("SELECT * FROM channel WHERE channelid = ?", (message.channel.id,))
            cmsg  = await message.channel.fetch_message(res[0][2])
            await cmsg.delete()
            view = discord.ui.View()
            view.add_item(discord.ui.Button(custom_id="recommend_thischannel", label="추천하기", style= discord.ButtonStyle.green))
            count = await message.channel.send(embed=discord.Embed(title=f"추천수: {res[0][3]}"), view=view)
            executeDB("UPDATE channel SET lasted_msg_id = ? WHERE channelid=?", (count.id, message.channel.id,), commit=True)



@client.event
async def on_interaction(interaction: discord.Interaction):
    if(interaction.type == discord.InteractionType.component):
        # if( interactio)
        if( interaction.data.get("custom_id") == "delete_channel"):
            if ( len(uobj := executeDB("SELECT * FROM channel WHERE channelid=?", ( interaction.channel.id,))) > 0 ):
                if( not uobj[0][0] == interaction.user.id and not interaction.user.guild_permissions.administrator):
                    await interaction.response.send_message(f"본인의 개인채널만 삭제 가능합니다.", ephemeral=True)
                    return


            await interaction.channel.delete()
            executeDB("DELETE FROM channel WHERE ownerid = ? AND channelid=?", (interaction.user.id, interaction.channel.id), commit=True)

            return
                
        if( interaction.data.get("custom_id") == "recommend_thischannel"):
            now = datetime.datetime.now()
            if ( len(executeDB("SELECT * FROM log WHERE userid = ? AND date=?", (interaction.user.id, f"{now.year}-{now.month}-{now.day}" ))) > 0 ):
                await interaction.response.send_message("추천은 하루에 한 번만 가능합니다.", ephemeral=True)
                return
            executeDB("INSERT INTO log VALUES (?,?)", (interaction.user.id, f"{now.year}-{now.month}-{now.day}" ), commit=True)       
            await interaction.response.send_message("추천 완료하였습니다.", ephemeral=True)
            executeDB("UPDATE channel SET counts = counts + 1 WHERE channelid=?", (interaction.channel.id,), commit=True)
            res = executeDB("SELECT * FROM channel WHERE channelid = ?", (interaction.channel.id,))
            cmsg  = await interaction.channel.fetch_message(res[0][2])
            await cmsg.delete()
            view = discord.ui.View()
            view.add_item(discord.ui.Button(custom_id="recommend_thischannel", label="추천하기", style= discord.ButtonStyle.green))
            count = await interaction.channel.send(embed=discord.Embed(title=f"추천수: {res[0][3]}"), view=view)
            executeDB("UPDATE channel SET lasted_msg_id = ? WHERE channelid=?", (count.id, interaction.channel.id,), commit=True)

            lst = executeDB("SELECT * FROM channel")
            lst.sort(key=lambda x:x[3])     
            lst.reverse()

            offset = 0
            for i in lst:
                if( i[1] == interaction.channel.id ):
                    break
                offset+= 1
            await interaction.channel.move( beginning=True, offset=offset)

            



        if( interaction.data.get("custom_id") == "create_custom_channel"):
            if ( len(uobj := executeDB("SELECT * FROM channel WHERE ownerid = ?", (interaction.user.id,))) > 0 ):
                await interaction.response.send_message(f"이미 개인 채널이 존재합니다. <#{uobj[0][1]}>", ephemeral=True)
            
                return 
            

            modal  =discord.ui.Modal(title="채널 명을 입력하여주세요", custom_id="channelnamemodal")
            modal.add_item(discord.ui.TextInput(label = "채널명", custom_id="modalinput", min_length=2, max_length=10, required=True))
            await interaction.response.send_modal(modal)
            
            def check():
                global channel_name
                def innerCheck(interaction2 : discord.Interaction):
                    global channel_name
                    if( interaction2.type == discord.InteractionType.modal_submit and interaction2.data.get("custom_id") == "channelnamemodal" and interaction2.user.id == interaction.user.id ):
 
                        return True
                    return False
                return innerCheck


            channel_name : discord.Interaction = await client.wait_for("interaction", check = check())
            await channel_name.response.send_message("채널이름이 작성되었습니다.", ephemeral=True)
            channel_name = channel_name.data.get("components")[0].get("components")[0].get("value")
            # modal.stop()


            category  : discord.CategoryChannel = None
            for i in interaction.guild.categories:
                if( i.id == personal_channel_category ):
                    category = i
                    break

            channel : discord.TextChannel = await category.create_text_channel(channel_name)
            # channel.move(offset=0)
            await interaction.followup.send(f"개인 채널이 생성되었습니다. <#{channel.id}>.", ephemeral=True)
            view = discord.ui.View()
            view.add_item(discord.ui.Button(custom_id="delete_channel", label="개인채널 닫기", style= discord.ButtonStyle.red))
            await channel.send(embed=discord.Embed(title=f"개인채널 ", description=f"<@{interaction.user.id}>님의 개인채널입니다. 아래 버튼을 이용하여 채널을 닫으실 수 있습니다."), view=view)
            
            view = discord.ui.View()
            view.add_item(discord.ui.Button(custom_id="recommend_thischannel", label="추천하기", style= discord.ButtonStyle.green))
            count = await channel.send(embed=discord.Embed(title=f"추천수: 0"), view=view)
            await channel.set_permissions(interaction.user, send_messages=True)
            executeDB("INSERT INTO channel VALUES (?,?,?,?)", (interaction.user.id, channel.id, count.id, 0),commit=True)


            

                    

client.run("")
