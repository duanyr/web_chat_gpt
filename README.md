# web_gpt_chat

## 具体功能

- 网页版ChatGPT聊天窗口实现 
- 应用openAI的流式数据获取能力，开单独线程实现消息获取流畅体验
- 应用redis的消息队列做数据处理
- python Django框架设计web服务端
- python gevent协程网络库提升并发性能


## 使用方法

1. 因为该功能是与openAI对接，最好准备一台欧洲或美洲的服务器，阿里云和腾讯云均可购买
2. 服务器配置好centos或ubuntu系统环境，将代码clone到主机上
3. 安装依赖，pip install -r requirements.txt
4. 运行服务，gunicorn chat.wsgi:application -w 1 -k gevent -b ip:port

## 联系作者
- wechat：dyrslds

## ChatGPT体验
- 作者一并将ChatGPT对话功能集成到微信公众号 奇点涌现，大家可以关注体验，日常也会分享一些ChatGPT和AI绘画的前沿用法

![avatar](png/奇点涌现.png)
