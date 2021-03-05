import os
import tempfile
from typing import Literal
import lavalink
import pydub

# Import Amazon Polly client library
import boto3
from discord import guild

from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]


class TextToSpeech(commands.Cog):

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=133335510675488768,
            force_registration=True,
        )
        self.last_track_info = None
        self.current_track = None
        default_config = {
            'padding': 700,
            'tts_lang': 'en',
            'sounds': {}
        }
        self.config.register_guild(**default_config)
        lavalink.register_event_listener(self.ll_check)

    def __unload(self):
        lavalink.unregister_event_listener(self.ll_check)

    @commands.command()
    async def dev(self, ctx):
        print(ctx.guild.id)

    @commands.command()
    async def tts(self, ctx, *, message: str):

        aws_access_key_id = await self.bot.get_shared_api_tokens("aws")
        if aws_access_key_id.get("aws_access_key_id") is None:
            return await ctx.send(
                "The AWS Access Key ID has not been set.\n\n"
                "Run `[p]set api aws aws_access_key_id,<yourkey>`"
            )

        aws_secret_access_key = await self.bot.get_shared_api_tokens("aws")
        if aws_secret_access_key.get("aws_secret_access_key") is None:
            return await ctx.send(
                "The AWS Secret Access Key has not been set.\n\n"
                "Run `[p]set api aws aws_secret_access_key,<yourkey>`"
            )

        aws_access_key_id = aws_access_key_id.get("aws_access_key_id")
        aws_secret_access_key = aws_secret_access_key.get("aws_secret_access_key")

        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send('You are not connected to a voice channel.')
            return

        polly_client = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name='eu-central-1').client('polly')

        response = polly_client.synthesize_speech(VoiceId='Brian',
                                                  OutputFormat='mp3',
                                                  Text=message)

        request_id = response['ResponseMetadata']['RequestId']
        tts_audio = response['AudioStream'].read()
        audio_file = os.path.join(tempfile.gettempdir(), ''.join(request_id + ".mp3"))

        file = open(audio_file, 'wb')
        file.write(tts_audio)
        file.close()

        audio_data = pydub.AudioSegment.from_mp3(audio_file)
        silence = pydub.AudioSegment.silent(duration=500)
        padded_audio = silence + audio_data + silence
        padded_audio.export(audio_file, format='mp3')

        try:
            await self.play_tts(ctx, ctx.author.voice.channel, audio_file)
        except TypeError:
            print("caught error")

    async def play_tts(self, ctx, voice_channel, filepath):

        try:
            player = lavalink.get_player(ctx.guild.id)
        except KeyError:
            player = await lavalink.connect(voice_channel)

        track = (await player.get_tracks(query=filepath))[0]

        if player.current is None:
            print("player.current is none")
            player.queue.append(track)
            self.current_track = track
            await player.play()
            return

        if self.current_track is not None:
            print("self.current_track is not none")
            player.queue.append(track)
            await player.skip()
            if self.current_track[1]:
                os.remove(self.current_track[0].uri)
            self.current_track = track
            return

        self.last_track_info = (player.current, player.position)
        self.current_track = track
        player.queue.insert(0, track)
        print(player.queue)
        player.queue.insert(1, player.current)
        print(player.queue)
        await player.skip()

    async def ll_check(self, player, event, reason):

        return

        # print("ll_check started")
        # print("queue" + str(player.queue))
        #
        # if self.current_track is None and self.last_track_info is None:
        #     print("notrack: " + str(self.current_track))
        #     return
        #
        # if event == lavalink.LavalinkEvents.TRACK_EXCEPTION and self.current_track is not None:
        #     print("exception: " + str(self.current_track))
        #     if self.current_track[1]:
        #         os.remove(self.current_track[0].uri)
        #     self.current_track = None
        #     return
        #
        # if event == lavalink.LavalinkEvents.TRACK_STUCK and self.current_track is not None:
        #     print("stuck: " + str(self.current_track))
        #     if self.current_track[1]:
        #         os.remove(self.current_track[0].uri)
        #     self.current_track = None
        #     await player.skip()
        #     return
        #
        # if event == lavalink.LavalinkEvents.TRACK_END and player.current is None and self.current_track is not None:
        #     print("end: " + str(self.current_track))
        #     if self.current_track[1]:
        #         os.remove(self.current_track[0].uri)
        #     self.current_track = None
        #     return
        #
        # if event == lavalink.LavalinkEvents.TRACK_END and self.last_track_info is not None and player.current.track_identifier == \
        #         self.last_track_info[0].track_identifier:
        #     print("last: " + str(self.current_track))
        #     print(str(self.last_track_info[0].uri))
        #     if self.current_track[1]:
        #         os.remove(self.current_track[0].uri)
        #     self.current_track = None
        #     await player.pause()
        #     await player.seek(self.last_track_info[1])
        #     await player.pause(False)
        #     self.last_track_info = None
        #
        # print("ll_check finished")

    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        # TODO: Replace this with the proper end user data removal handling.
        super().red_delete_data_for_user(requester=requester, user_id=user_id)
