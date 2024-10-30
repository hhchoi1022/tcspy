


#%%%
from slack_sdk import WebClient

#%%

class SlackConnector():
    
    def __init__(self,
                 token_path : str  = '/home/kds/.config/slack/slack_token_7dt_obseration_alert.txt',
                 default_channel_id : str = 'C07SREPTWFM'):
        token = open(token_path, 'r').read()
        self.client = WebClient(token = token)
        self.channel_id = default_channel_id
    
    def get_channel_id(self, channel_name):
        """
        get channel id based on the channel name
        """
        # conversations_list() 
        private_channels = self.client.conversations_list(types="private_channel").data['channels']
        public_channels = self.client.conversations_list(types="public_channel").data['channels']
        # channel information
        channels = private_channels + public_channels
        channel = list(filter(lambda c: c["name"] == channel_name, channels))
        
        if len(channel) == 0:
            raise ValueError(f"Channel {channel_name} not found")
        else:
            return channel[0]["id"]
    
    def select_channel(self, channel_name):
        """
        select channel based on the channel name
        """
        self.channel_id = self.get_channel_id(channel_name)

    def get_message_ts(self, match_string):
        """
        슬랙 채널 내 메세지 조회
        """
        if self.channel_id is None:
            raise ValueError("Channel is not selected")
        # conversations_history() 메서드 호출
        result = self.client.conversations_history(channel=self.channel_id)
        # 채널 내 메세지 정보 딕셔너리 리스트
        messages = result.data['messages']
        # 채널 내 메세지가 query와 일치하는 메세지 딕셔너리 쿼리
        matched_messages = list(filter(lambda m: match_string in m["text"], messages))
        # 해당 메세지ts 파싱
        if len(matched_messages) == 0:
            print(f"Message {match_string} not found")   
            return None
        message_ts = matched_messages[0]["ts"]
        return message_ts

    def post_thread_message(self, message_ts, text):
        """
        슬랙 채널 내 메세지의 Thread에 댓글 달기
        """
        if self.channel_id is None:
            raise ValueError("Channel is not selected")
        # chat_postMessage() 메서드 호출
        result = self.client.chat_postMessage(
            channel=self.channel_id,
            text = text,
            thread_ts = message_ts
        )
        print(f'Thread message posted: text = {text}')
        return result

    def post_message(self, text):
        """
        슬랙 채널에 메세지 보내기
        """
        # chat_postMessage() 메서드 호출
        if self.channel_id is None:
            raise ValueError("Channel is not selected")
        result = self.client.chat_postMessage(
            channel=self.channel_id,
            text=text
        )
        print(f'Message posted: text = {text}')
        return result
# %%
if __name__ == '__main__':
    A = SlackConnector()
    #ts = A.get_message_ts('Test message')
    #A.post_thread_message(A.channel_id, ts, 'Thread message')
# %%
