import discord
from main import mongo
from datetime import datetime, timezone, tzinfo
from discord.ext import commands
import aiohttp
import traceback
import asyncio
import utils
from typing import Union
import os

api_key = os.getenv("api_key")

class Military(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.bot.bg_task = self.bot.loop.create_task(self.wars())

    async def add_to_thread(self, thread, atom_id: Union[str, int], atom: dict = None):
        await asyncio.sleep(1.1)
        person = utils.find_user(self, atom_id)
        if person == {}:
            print("tried to add, but could not find", atom_id)
            if atom:
                await thread.send(f"I was unable to add {atom['leader_name']} of {atom['nation_name']} to the thread. Have they not linked their nation with their discord account?")
            else:
                await thread.send(f"I was unable to add nation {atom_id} to the thread. Have they not linked their nation with their discord account?")
            return
        user = await self.bot.fetch_user(person['user'])
        try:
            await thread.add_user(user)
        except Exception as e:
            await thread.send(f"I was unable to add {user} to the thread.\n```{e}```")
    
    async def remove_from_thread(self, thread, atom_id: Union[str, int], atom: dict = None):
        await asyncio.sleep(1.1)
        person = utils.find_user(self, atom_id)
        if person == {}:
            print("tried to remove, but could not find", atom_id)
            if atom:
                await thread.send(f"I was unable to remove {atom['leader_name']} of {atom['nation_name']} from the thread. Have they not linked their nation with their discord account?")
            else:
                await thread.send(f"I was unable to remove nation {atom_id} from the thread. Have they not linked their nation with their discord account?")
            return
        user = await self.bot.fetch_user(person['user'])
        try:
            await thread.remove_user(user)
        except:
            await thread.send(f"I was unable to remove {user} from the thread.")

    async def wars(self):
        await self.bot.wait_until_ready()
        channel_id = int(os.getenv("channel_id"))
        channel = self.bot.get_channel(channel_id)
        debug_channel = self.bot.get_channel(739155202640183377)
        prev_wars = None

        async def cthread(war, non_atom, atom):
            await asyncio.sleep(1.1)
            attack_logs = {"id": war['id'], "attacks": [], "detected": datetime.utcnow(), "finished": False}
            mongo.war_logs.insert_one(attack_logs)

            url = f"https://politicsandwar.com/nation/war/timeline/war={war['id']}"
            embed = discord.Embed(title=f"New {war['war_type'].lower().capitalize()} War", url=url, description=f"[{war['attacker']['nation_name']}](https://politicsandwar.com/nation/id={war['attacker']['id']}) declared a{'n'[:(len(war['war_type'])-5)^1]} {war['war_type'].lower()} war on [{war['defender']['nation_name']}](https://politicsandwar.com/nation/id={war['defender']['id']})", color=0x2F3136)
            name = f"{non_atom['nation_name']} ({non_atom['id']})"
            found = False

            for thread in channel.threads:
                if f"({non_atom['id']})" in thread.name:
                    found = True
                    matching_thread = thread
                    break
            if not found:
                async for thread in channel.archived_threads():
                    if f"({non_atom['id']})" in thread.name:
                        found = True
                        matching_thread = thread
                        break
            if not found:
                message = await channel.send(embed=embed)
                try:
                    thread = await channel.create_thread(name=name, message=message, auto_archive_duration=4320, type=discord.ChannelType.private_thread, reason="War declaration")
                except:
                    thread = await channel.create_thread(name=name, message=message, auto_archive_duration=1440, type=discord.ChannelType.private_thread, reason="War declaration")
                await self.add_to_thread(thread, atom['id'], atom)
            elif found:
                await matching_thread.send(embed=embed)
                await self.add_to_thread(matching_thread, atom['id'], atom)

            return attack_logs

        async def attack_check(attack, new_war):
            if attack['type'] in ["MISSILEFAIL", "MISSILE", "NUKE", "NUKEFAIL"]:
                if {"id": attack['cityid']} in new_war['attacker']['cities']:
                    attacker = new_war['defender']['id']
                else:
                    attacker = new_war['attacker']['id']
            elif attack['type'] == "FORTIFY":
                attacker = None
            elif attack['success'] > 0:
                attacker = attack['victor']
            else:
                attacker = [new_war['attacker']['id'], new_war['defender']['id']]
                attacker.remove(attack['victor'])
                attacker = attacker[0]
            return attacker

        async def smsg(attacker_id, attack, war, atom, non_atom, peace):
            await asyncio.sleep(1.1)
            embed = discord.Embed(title=f"New {war['war_type'].lower().capitalize()} War", description=f"[{war['attacker']['nation_name']}](https://politicsandwar.com/nation/id={war['attacker']['id']}) declared a{'n'[:(len(war['war_type'])-5)^1]} {war['war_type'].lower()} war on [{war['defender']['nation_name']}](https://politicsandwar.com/nation/id={war['defender']['id']})", color=0x2F3136)
            
            found = False
            for thread in channel.threads:
                if f"({non_atom['id']})" in thread.name:
                    matching_thread = thread
                    found = True
                    break
            
            if not found:
                async for thread in channel.archived_threads():
                    if f"({non_atom['id']})" in thread.name:
                        matching_thread = thread
                        found = True
                        person = utils.find_user(self, atom['id'])
                        if not person:
                            print("tried to add to archived thread, but could not find", atom['id'])
                            await thread.send(f"I was unable to add nation {atom['id']} to the thread. Have they not linked their nation with their discord account?")
                            break
                        user = await self.bot.fetch_user(person['user'])
                        try:
                            await thread.add_user(user)
                        except:
                            pass
                        break
            
            if not found:
                print("making thread")
                await cthread(war, non_atom, atom)
                for thread in channel.threads:
                    if f"({non_atom['id']})" in thread.name:
                        print("found thread")
                        matching_thread = thread
                        found = True
                        break
                
            if found:
                thread = matching_thread
                url = f"https://politicsandwar.com/nation/war/timeline/war={war['id']}"
                if peace != None:
                    embed = discord.Embed(title="Peace offering", url=url, description=f"[{peace['offerer']['nation_name']}](https://politicsandwar.com/nation/id={peace['offerer']['id']}) is offering peace to [{peace['reciever']['nation_name']}](https://politicsandwar.com/nation/id={peace['reciever']['id']}). The peace offering will be canceled if either side performs an act of aggression.", color=0xffffff)
                    await thread.send(embed=embed)
                    return
                footer = f"<t:{round(datetime.strptime(attack['date'], '%Y-%m-%d %H:%M:%S%z').timestamp())}:R> <t:{round(datetime.strptime(attack['date'], '%Y-%m-%d %H:%M:%S%z').timestamp())}>"
                if attack['type'] != "FORTIFY":
                    if attack['type'] in ["GROUND", "NAVAL", "AIRVINFRA", "AIRVSOLDIERS", "AIRVTANKS", "AIRVMONEY", "AIRVSHIPS", "AIRVAIR"]:
                        for nation in [war['attacker'], war['defender']]:
                            if nation['id'] == attacker_id:
                                attacker_nation = nation
                            elif nation['id'] != attacker_id:
                                defender_nation = nation

                        colors = [0xff0000, 0xffff00, 0xffff00, 0x00ff00]
                        if attacker_nation['id'] == non_atom['id']:
                            colors.reverse()

                        if attack['success'] == 3:
                            success = "Immense Triumph"
                        elif attack['success'] == 2:
                            success = "Moderate Success"
                        elif attack['success'] == 1:
                            success = "Pyrrhic Victory"
                        elif attack['success'] == 0:
                            success = "Utter Failure"

                        description = f"Success: {success}"

                        if attack['type'] == "GROUND":
                            if attack['aircraft_killed_by_tanks']:
                                aircraft = f"\n{attack['aircraft_killed_by_tanks']:,} aircraft"
                            else:
                                aircraft = ""
                            title = "Ground battle"
                            att_casualties = f"{attack['attcas1']:,} soldiers\n{attack['attcas2']:,} tanks"
                            def_casualties = f"{attack['defcas1']:,} soldiers\n{attack['defcas2']:,} tanks{aircraft}"
                        elif attack['type'] == "NAVAL":
                            title = "Naval Battle"
                            att_casualties = f"{attack['attcas1']:,} ships"
                            def_casualties = f"{attack['defcas1']:,} ships"
                        elif attack['type'] == "AIRVINFRA":
                            title = "Airstrike targeting infrastructure"
                            att_casualties = f"{attack['attcas1']:,} planes"
                            def_casualties = f"{attack['defcas1']:,} planes\n{attack['infradestroyed']} infra (${attack['infra_destroyed_value']:,})"
                        elif attack['type'] == "AIRVSOLDIERS":
                            title = "Airstrike targeting soldiers"
                            att_casualties = f"{attack['attcas1']:,} planes"
                            def_casualties = f"{attack['defcas1']:,} planes\n{attack['defcas2']} soldiers"
                        elif attack['type'] == "AIRVTANKS":
                            title = "Airstrike targeting tanks"
                            att_casualties = f"{attack['attcas1']:,} planes"
                            def_casualties = f"{attack['defcas1']:,} planes\n{attack['defcas2']} tanks"
                        elif attack['type'] == "AIRVMONEY":
                            title = "Airstrike targeting money"
                            att_casualties = f"{attack['attcas1']:,} planes"
                            def_casualties = f"{attack['defcas1']:,} planes\n{attack['defcas2']} money"
                        elif attack['type'] == "AIRVSHIPS":
                            title = "Airstrike targeting ships"
                            att_casualties = f"{attack['attcas1']:,} planes"
                            def_casualties = f"{attack['defcas1']:,} planes\n{attack['defcas2']} ships"
                        elif attack['type'] == "AIRVAIR":
                            title = "Airstrike targeting aircraft"
                            att_casualties = f"{attack['attcas1']:,} planes"
                            def_casualties = f"{attack['defcas1']:,} planes"
                        try:
                            aaa_link = f"[{attacker_nation['alliance']['name']}](https://politicsandwar.com/alliance/id={attacker_nation['alliance_id']})"
                        except:
                            aaa_link = "No alliance"
                        try:
                            daa_link = f"[{defender_nation['alliance']['name']}](https://politicsandwar.com/alliance/id={defender_nation['alliance_id']})"
                        except:
                            daa_link = "No alliance"

                        embed = discord.Embed(title=title, description=description, color=colors[attack['success']], url=url)
                        embed.add_field(name=f"Attacker", value=f"[{attacker_nation['nation_name']}](https://politicsandwar.com/nation/id={attacker_nation['id']})\n{aaa_link}\n\n**Casualties**:\n{att_casualties}")
                        embed.add_field(name=f"Defender", value=f"[{defender_nation['nation_name']}](https://politicsandwar.com/nation/id={defender_nation['id']})\n{daa_link}\n\n**Casualties**:\n{def_casualties}")
                        embed.add_field(name="\u200b", value=footer, inline=False)
                        await thread.send(embed=embed)
                        mongo.war_logs.find_one_and_update({"id": war['id']}, {"$push": {"attacks": attack['id']}})
                    elif attack['type'] in ["PEACE", "VICTORY", "ALLIANCELOOT", "EXPIRATION"]:
                        if attack['type'] == "PEACE":
                            title = "White peace"
                            color = 0xffFFff
                            content = f"The peace offer was accepted, and [{war['attacker']['nation_name']}](https://politicsandwar.com/nation/id={war['attacker']['id']}) is no longer fighting an offensive war against [{war['defender']['nation_name']}](https://politicsandwar.com/nation/id={war['defender']['id']})."
                        elif attack['type'] == "VICTORY":
                            if attack['victor'] == atom['id']:
                                title = "Victory"
                                color = 0x00ff00
                            else:
                                title = "Defeat"
                                color = 0xff0000
                            loot = attack['loot_info'].replace('\r\n                            ', '')
                            content = f"[{war['attacker']['nation_name']}](https://politicsandwar.com/nation/id={war['attacker']['id']}) is no longer fighting an offensive war against [{war['defender']['nation_name']}](https://politicsandwar.com/nation/id={war['defender']['id']}).\n\n{loot}"
                        elif attack['type'] == "ALLIANCELOOT":
                            if atom['nation_name'] in attack['loot_info']:
                                color = 0x00ff00
                            else:
                                color = 0xff0000
                            title = "Alliance loot"
                            loot = attack['loot_info'].replace('\r\n                            ', '')
                            content = f"{loot}"
                        elif attack['type'] == "EXPIRATION":
                            title = "War expiration"
                            color = 0xffFFff
                            content = f"The war has lasted 5 days, and has consequently expired. [{war['attacker']['nation_name']}](https://politicsandwar.com/nation/id={war['attacker']['id']}) is no longer fighting an offensive war against [{war['defender']['nation_name']}](https://politicsandwar.com/nation/id={war['defender']['id']})."
                        embed = discord.Embed(title=title, url=url, description=content, color=color)
                        embed.add_field(name="\u200b", value=footer, inline=False)
                        await thread.send(embed=embed)
                        mongo.war_logs.find_one_and_update({"id": war['id']}, {"$push": {"attacks": attack['id']}})
                    else:
                        for nation in [war['attacker'], war['defender']]:
                            if nation['id'] == attacker_id:
                                attacker_nation = nation
                            elif nation['id'] != attacker_id:
                                defender_nation = nation

                        colors = [0xff0000, 0x00ff00]
                        if attacker_nation['id'] == non_atom['id']:
                            colors.reverse()

                        if attack['type'] == "MISSILE":
                            title = "Missile"
                            content = f"[{attacker_nation['nation_name']}](https://politicsandwar.com/nation/id={attacker_nation['id']}) launched a missile upon [{defender_nation['nation_name']}](https://politicsandwar.com/nation/id={defender_nation['id']}), destroying {attack['infradestroyed']} infra (${attack['infra_destroyed_value']:,}) and {attack['improvementslost']} improvement{'s'[:attack['improvementslost']^1]}."
                        elif attack ['type'] == "MISSILEFAIL":
                            title = "Failed missile"
                            content = f"[{attacker_nation['nation_name']}](https://politicsandwar.com/nation/id={attacker_nation['id']}) launched a missile upon [{defender_nation['nation_name']}](https://politicsandwar.com/nation/id={defender_nation['id']}), but the missile was shot down."
                        elif attack['type'] == "NUKE":
                            title = "Nuke"
                            content = f"[{attacker_nation['nation_name']}](https://politicsandwar.com/nation/id={attacker_nation['id']}) launched a nuclear weapon upon [{defender_nation['nation_name']}](https://politicsandwar.com/nation/id={defender_nation['id']}), destroying {attack['infradestroyed']} infra (${attack['infra_destroyed_value']:,}) and {attack['improvementslost']} improvement{'s'[:attack['improvementslost']^1]}."
                        elif attack['type'] == "NUKEFAIL":
                            title = "Failed nuke"
                            content = f"[{attacker_nation['nation_name']}](https://politicsandwar.com/nation/id={attacker_nation['id']}) launched a nuclear weapon upon [{defender_nation['nation_name']}](https://politicsandwar.com/nation/id={defender_nation['id']}), but the nuke was shot down."
                    
                        embed = discord.Embed(title=title, url=url, description=content, color=colors[attack['success']])
                        embed.add_field(name="\u200b", value=footer, inline=False)
                        await thread.send(embed=embed)
                        mongo.war_logs.find_one_and_update({"id": war['id']}, {"$push": {"attacks": attack['id']}})
                else:
                    if war['att_fortify'] and war['def_fortify']:
                        content = f"{war['attacker']['nation_name']} and {war['defender']['nation_name']} are now fortified."
                        color = 0xffff00
                    elif war['att_fortify']:
                        content = f"{war['attacker']['nation_name']} is now fortified."
                        if war['attacker'] == atom:
                            color = 0x00ff00
                        else:
                            color = 0xff0000
                    elif war['def_fortify']:
                        content = f"{war['defender']['nation_name']} is now fortified."
                        if war['defender'] == atom:
                            color = 0x00ff00
                        else:
                            color = 0xff0000
                    else:
                        content = f"{war['attacker']['nation_name']} or {war['defender']['nation_name']} fortified (idk who due to api limitations), then subsequently attacked, losing the fortified effect."
                        color = 0xffffff
                    
                    embed = discord.Embed(title="Fortification", url=url, description=content, color=color)
                    embed.add_field(name="\u200b", value=footer, inline=False)
                    await thread.send(embed=embed)
                    mongo.war_logs.find_one_and_update({"id": war['id']}, {"$push": {"attacks": attack['id']}})
            else:
                print("could not find or create thread", war['id'], peace)

        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    has_more_pages = True
                    n = 1
                    while has_more_pages:
                        async with session.post(f"https://api.politicsandwar.com/graphql?api_key={api_key}", json={'query': f"{{wars(alliance_id:[4729,7531] page:{n} active:true){{paginatorInfo{{hasMorePages}} data{{id att_fortify war_type def_fortify attpeace defpeace turnsleft date att_alliance_id def_alliance_id attacker{{nation_name leader_name alliance{{name}} id num_cities cities{{id}}}} defender{{nation_name leader_name alliance{{name}} id num_cities cities{{id}}}} attacks{{type id date loot_info victor moneystolen success cityid resistance_eliminated infradestroyed infra_destroyed_value improvementslost aircraft_killed_by_tanks attcas1 attcas2 defcas1 defcas2}}}}}}}}"}) as temp:
                            n += 1
                            try:
                                wars = (await temp.json())['data']['wars']['data']
                                has_more_pages = (await temp.json())['data']['wars']['paginatorInfo']['hasMorePages']
                            except:
                                print((await temp.json())['errors'])
                                await asyncio.sleep(60)
                                continue
                            if prev_wars == None:
                                prev_wars = wars
                                continue
                    has_more_pages = True
                    n = 1
                    min_id = 0
                    done_wars = []
                    while has_more_pages:
                        async with session.post(f"https://api.politicsandwar.com/graphql?api_key={api_key}", json={'query': f"{{wars(alliance_id:[4729,7531] page:{n} min_id:{min_id} active:false orderBy:{{column: ID order:DESC}}){{paginatorInfo{{hasMorePages}} data{{id att_fortify war_type def_fortify attpeace defpeace turnsleft date att_alliance_id def_alliance_id attacker{{nation_name leader_name alliance{{name}} id num_cities cities{{id}}}} defender{{nation_name leader_name alliance{{name}} id num_cities cities{{id}}}} attacks{{type id date loot_info victor moneystolen success cityid resistance_eliminated infradestroyed infra_destroyed_value improvementslost aircraft_killed_by_tanks attcas1 attcas2 defcas1 defcas2}}}}}}}}"}) as temp1:
                            n += 1
                            try:
                                all_wars = (await temp1.json())['data']['wars']['data']
                                has_more_pages = (await temp1.json())['data']['wars']['paginatorInfo']['hasMorePages']
                                for war in all_wars:
                                    if war['turnsleft'] <= 0:
                                        declaration = datetime.strptime(war['date'], '%Y-%m-%d %H:%M:%S%z').replace(tzinfo=None)
                                        if (datetime.utcnow() - declaration).days <= 5:
                                            done_wars.append(war)
                            except:
                                print((await temp1.json())['errors'])
                                await asyncio.sleep(60)
                                continue
                    print(len(done_wars))
                    for new_war in wars:
                        if new_war['att_alliance_id'] in ['4729', '7531']: ## CHANGE T0 ATOM ---------------------------------------------------------
                            atom = new_war['attacker']
                            non_atom = new_war['defender']
                        else:
                            atom = new_war['defender']
                            non_atom = new_war['attacker']
                        attack_logs = mongo.war_logs.find_one({"id": new_war['id']})
                        if not attack_logs:
                            attack_logs = await cthread(new_war, non_atom, atom)
                        for old_war in prev_wars:
                            if new_war['id'] == old_war['id']:
                                if new_war['attpeace'] and not old_war['attpeace']:
                                    peace_obj = {"offerer": new_war['attacker'], "reciever": new_war['defender']}
                                    await smsg(None, None, new_war, atom, non_atom, peace_obj)
                                elif new_war['defpeace'] and not old_war['defpeace']:
                                    peace_obj = {"offerer": new_war['defender'], "reciever": new_war['attacker']}
                                    await smsg(None, None, new_war, atom, non_atom, peace_obj)
                                break
                        for attack in new_war['attacks']:
                            if attack['id'] not in attack_logs['attacks']:
                                attacker = await attack_check(attack, new_war)
                                await smsg(attacker, attack, new_war, atom, non_atom, None)
                    for done_war in done_wars:
                        if done_war['att_alliance_id'] in ['4729', '7531']: ## CHANGE T0 ATOM ---------------------------------------------------------
                            atom = done_war['attacker']
                            non_atom = done_war['defender']
                        else:
                            atom = done_war['defender']
                            non_atom = done_war['attacker']
                        attack_logs = mongo.war_logs.find_one({"id": done_war['id']})
                        if not attack_logs:
                            attack_logs = await cthread(done_war, non_atom, atom)
                        elif attack_logs['finished']:
                            continue
                        for attack in done_war['attacks']:
                            if attack['id'] not in attack_logs['attacks']:
                                attacker = await attack_check(attack, done_war)
                                await smsg(attacker, attack, done_war, atom, non_atom, None)
                        if len(done_war['attacks']) == 0:
                            attack = {"type": "EXPIRATION", "id": -1, "date": datetime.strftime(datetime.utcnow().replace(tzinfo=timezone.utc), '%Y-%m-%d %H:%M:%S%z')}
                            await smsg(None, attack, done_war, atom, non_atom, None)
                        elif done_war['attacks'][-1]['type'] not in ["PEACE", "VICTORY", "ALLIANCELOOT"]:
                            attack = {"type": "EXPIRATION", "id": -1, "date": datetime.strftime(datetime.utcnow().replace(tzinfo=timezone.utc), '%Y-%m-%d %H:%M:%S%z')}
                            await smsg(None, attack, done_war, atom, non_atom, None)
                        for thread in channel.threads:
                            if f"({non_atom['id']})" in thread.name:
                                await self.remove_from_thread(thread, atom['id'], atom)
                                members = thread.fetch_members()
                                member_count = 0
                                for member in members:
                                    user = await self.bot.fetch_user(member['id'])
                                    if user.bot:
                                        continue
                                    else:
                                        member_count += 1
                                if member_count == 0:
                                    await thread.edit(archived=True)
                                mongo.war_logs.find_one_and_update({"id": done_war['id']}, {"$set": {"finished": True}})
                                break
                if len(done_wars) > 0:
                    min_id = done_wars[0]['id']
                prev_wars = wars
                await asyncio.sleep(60)
            except:
                await debug_channel.send(f"I encountered an error whilst scanning for wars:```{traceback.format_exc()}```")

def setup(bot):
    bot.add_cog(Military(bot))