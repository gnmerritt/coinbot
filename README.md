# coinbot

## install

Need python 3.6+, pip

```
pip install -r requirements.txt
```

Set up your config file to include your slack & exchange API keys

## usage

```
# usage: python strategies/cron.py <config_file> <command one> <command two> <...>
# e.g.
python strategies/cron.py config.yaml update tick strengths
```

I have the bot processing (`update tick`) every 10 mins and displaying account info and strengths a couple times per day. All logging and error handling goes to a slack channel.

## slack slash commands

if desired, you can run the webserver to hook up slack slash commands. you'll need to configure a new application inside your slack instance and point it at your webserver. once you do that you can do `/coinbot account` etc. to run the same cron commands inside your slack channel

```
python strategies/slash_commands.py config.yaml
```
