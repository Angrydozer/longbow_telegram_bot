import telebot
import pandas as pd
import re
import datetime as dt
import matplotlib.pyplot as plt
from telebot.types import ReplyKeyboardRemove

# pogacts
# token = "вырезано"
# longbow
token = "вырезано"
bot = telebot.TeleBot(token)
location_datafile = "data.csv"
location_config = "config.csv"

# basic info
temp = {"time": "", "item": "", "ins": "", "other": "", "value": ""}
# read config from prepared csv (excel)
config = pd.read_csv(location_config, index_col=0)
config = config.T.to_dict()
# open main datafile
df = pd.read_csv(location_datafile, index_col=0)

# lists for buttons
parameters = {}
menu = []
for key in config:
    menu.append(key)
    if config[key]["ins_existance"]:
        parameters[key] = config[key]["ins_options"].split(", ")

num_ocb = 5  # number of out-config buttons, count below
# add NEW ones to the start
menu = menu + ["📊 stats", "📥 get csv", "📆 change date", "📄 last 5", "❌ delete last"]
parameters["menu"] = menu


# function for setting keyboard rows
def set_keyboard_rows(buttons, keyboard):
    modulo = len(buttons) % 3
    while len(buttons) >= 3:
        keyboard.row(buttons[0], buttons[1], buttons[2])
        buttons = buttons[3:]
    if modulo == 1:
        keyboard.row(buttons[0])
    elif modulo == 2:
        keyboard.row(buttons[0], buttons[1])


# keyboard menu
keyboard_menu = telebot.types.ReplyKeyboardMarkup()
btn_menu = [telebot.types.KeyboardButton(parameters["menu"][x]) for x in range(len(parameters["menu"]))]
set_keyboard_rows(btn_menu, keyboard_menu)

# keyboard nums
keyboard_nums = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
btn_nums = ["0.25", "0.5", "1", "1.5", "2", "3", "4", "5", "6", "7", "8", "9"]
set_keyboard_rows(btn_nums, keyboard_nums)


# is keyboard nums needed?
def keyboard_def(item):
    global keyboard_nums
    global config

    if config[item]["num_keyboard"] == 0:
        return ReplyKeyboardRemove()
    else:
        return keyboard_nums


# secondary keyboards creating
keyboards = {}
for par in list(parameters.keys())[:-1]:  # is because -1 key in parameters is menu, but keyboard created separately
    keyboard_temp = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_temp = [telebot.types.KeyboardButton(parameters[par][x]) for x in range(len(parameters[par]))]
    set_keyboard_rows(btn_temp, keyboard_temp)
    keyboards[par] = keyboard_temp
    del keyboard_temp
    del btn_temp


# function for adding data to csv
def add_data(added_row):
    global df
    df = pd.concat([df, pd.Series(temp, index=temp.keys()).to_frame().T]).reset_index(drop=True)
    df.to_csv(location_datafile, header=True, index=True)


# function for checking user id
def check_user(user_id):
    if user_id != 155295695:
        bot.send_message(user_id, "Не пытайтесь меня обмануть, вы не Коля 😡")
        return exit()


# function for deleting last row in csv
def del_data():
    global df
    df = df.iloc[:-1]
    df.to_csv(location_datafile, header=True, index=True)


# function for replacing date in selected row
def change_date(row_index, new_date):
    global df
    #  df.replace(df.loc[int(row_index), "time"], new_date, inplace=True)
    df.loc[int(row_index), "time"] = new_date
    df.to_csv(location_datafile, header=True, index=True)


# function to make df view readable in chat
def make_df_readable(df_slice):
    # only head(?) or tail(?)
    # df.loc and df.iloc input don't work
    msg = "[index]"
    for header in df_slice.columns:
        msg = msg + " - [" + str(header) + "]"
    for row_index in range(df_slice.shape[0]):
        msg = msg + "\n" + str(df_slice.index[row_index])
        for column_index in range(df_slice.shape[1]):
            if pd.isna(df_slice.iloc[row_index, column_index]) or df_slice.iloc[row_index, column_index] == "":
                msg = msg + " - ..."
            else:
                msg = msg + " - " + str(df_slice.iloc[row_index, column_index])
    return msg


# function return all other values for selected item
def show_others(item, ins):
    global df
    global temp
    if ins == "other":
        msg = "\n\nИспользуемые ключи:"
        for value in list(
                df[(df["item"] == item) & (df["ins"] == "other")].groupby(["other"])["other"].count().sort_values(
                    ascending=False).keys()):
            msg = msg + "\n" + str(value)
        if msg == "\n\nИспользуемые ключи:":
            msg = "\n\nЕще нет ни одного ключа в others к " + item
        return msg
    else:
        return ""


# function return all key values for any_action
def show_any_actions(item):
    global df
    global temp
    if item == "any_action":
        msg = "\n\nИспользуемые ключи:"
        for value in list(
                df[df["item"] == "any_action"].groupby(["value"])["value"].count().sort_values(ascending=False).keys()):
            msg = msg + "\n" + str(value)
        if msg == "\n\nИспользуемые ключи:":
            msg = "\n\nЕще нет ни одного ключа к any_action"
        return msg
    else:
        return ""


# /start handler
@bot.message_handler(commands=['start'])
def start_handler(message):
    check_user(message.chat.id)
    bot.send_message(message.chat.id, "Бот активирован, теперь можно добавлять новые записи в хранилище",
                     reply_markup=keyboard_menu)


# menu handler
@bot.message_handler(func=lambda message: message.text in parameters["menu"])
def menu_handler(message):
    check_user(message.chat.id)
    global df
    if message.text == parameters["menu"][-5]:
        # change date of selected row
        msg = bot.send_message(message.chat.id,
                               "По каким данным вы хотите получить статистику? (формат item*days)",
                               reply_markup=ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, askPrintStats)
    elif message.text == parameters["menu"][-4]:
        # get csv
        global location_datafile
        with open(location_datafile, "rb") as data_get_csv:
            data_get_csv_file = data_get_csv.read()
            msg = bot.send_document(message.chat.id, data_get_csv_file, caption=location_datafile)
    elif message.text == parameters["menu"][-3]:
        # change date of selected row
        msg = bot.send_message(message.chat.id,
                               "Введите новую дату/индекс строки, где нужно заменить дату (в формате {0}/8)".format(
                                   dt.datetime.fromtimestamp(message.date).strftime("%y-%m-%d %H:%M")),
                               reply_markup=ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, askDateChange)
    elif message.text == parameters["menu"][-2]:
        # show last 5 rows in csv
        bot.send_message(message.chat.id,
                         "Последние 5 строк\n\n" + make_df_readable(df.tail()),
                         reply_markup=keyboard_menu)
    elif message.text == parameters["menu"][-1]:
        # delete last row in csv
        del_data()
        bot.send_message(message.chat.id,
                         "Последняя строка удалена\n\n" + make_df_readable(df.tail()),
                         reply_markup=keyboard_menu)
    elif config[message.text]["ins_existance"] == 1:
        # ins_existance = 1
        temp["item"] = message.text
        msg = bot.send_message(message.chat.id,
                               config[message.text]["ins_msg"],
                               reply_markup=keyboards[message.text])
        bot.register_next_step_handler(msg, askIns)
    elif config[message.text]["ins_existance"] == 0:
        # ins_existance = 0
        temp["item"] = message.text
        msg = bot.send_message(message.chat.id,
                               config[message.text]["value_msg"] + show_any_actions(message.text),
                               reply_markup=keyboard_def(temp["item"]))
        bot.register_next_step_handler(msg, askValue)


def askIns(message):
    if not message.text in parameters[temp["item"]]:
        msg = bot.send_message(message.chat.id, "❗️ Вы должны выбрать один из предлагаемых вариантов")
        bot.register_next_step_handler(msg, askIns)
        return
    temp["ins"] = message.text

    # if friends or activities then no value
    if temp["item"] == "friends" or temp["item"] == "activities":
        temp["time"] = dt.datetime.fromtimestamp(message.date).strftime("%y-%m-%d %H:%M")
        add_data(temp)
        temp.update({"time": "", "item": "", "ins": "", "other": "", "value": ""})

        bot.send_message(message.chat.id,
                         "✅ Информация добавлена\n" + make_df_readable(df.tail(1)),
                         reply_markup=keyboard_menu)
        return

    msg = bot.send_message(message.chat.id,
                           config[temp["item"]]["value_msg"] + show_others(temp["item"], message.text),
                           reply_markup=keyboard_def(temp["item"]))
    bot.register_next_step_handler(msg, askValue)


def askValue(message):
    global temp
    global df

    # if ins = other, then input must be started with other_text*value
    if temp["ins"] == "other":
        if not re.match("^[^\*]+[\*]{1}" + config[temp["item"]]["value_re"][1:], message.text):
            msg = bot.send_message(message.chat.id, "❗ Вы ввели некорректное значение, попробуйте еще раз!")
            bot.register_next_step_handler(msg, askValue)
            return
        else:
            # splitting other and value
            other_arr = [match.groupdict() for match in
                         re.finditer("^(?P<other>[^\*]+)([\*]{1})(?P<value>.+)$", message.text)]
            print()
            temp["other"] = other_arr[0]["other"]
            temp["value"] = other_arr[0]["value"]
    else:
        if not re.match(config[temp["item"]]["value_re"], message.text):
            msg = bot.send_message(message.chat.id, "❗ Вы ввели некорректное значение, попробуйте еще раз!")
            bot.register_next_step_handler(msg, askValue)
            return
        else:
            temp["value"] = message.text

    temp["time"] = dt.datetime.fromtimestamp(message.date).strftime("%y-%m-%d %H:%M")
    add_data(temp)
    temp.update({"time": "", "item": "", "ins": "", "other": "", "value": ""})

    bot.send_message(message.chat.id,
                     "✅ Информация добавлена\n" + make_df_readable(df.tail(1)),
                     reply_markup=keyboard_menu)


def askDateChange(message):
    global df
    if not re.match("^[0-9]{2}\-[0-9]{1,2}\-[0-9]{1,2}\s[0-9]{1,2}\:[0-9]{2}\/[0-9]{1,6}$", message.text):
        msg = bot.send_message(message.chat.id, "❗ Вы ввели некорректное значение, попробуйте еще раз!")
        bot.register_next_step_handler(msg, askDateChange)
        return
    DateChangeInput = re.match("(?P<new_date>[^\/]+)(\/)(?P<row_index>[0-9]+)", message.text).groupdict()
    if int(DateChangeInput["row_index"]) > int(df.index[-1]):
        msg = bot.send_message(message.chat.id, "❗ Такой строки не существует, попробуйте еще раз!")
        bot.register_next_step_handler(msg, askDateChange)
        return
    bot.send_message(message.chat.id,
                     "✅ Дата скорректирована\n" + df["time"][int(DateChangeInput["row_index"])] + " >>> " +
                     DateChangeInput["new_date"],
                     reply_markup=keyboard_menu)
    change_date(DateChangeInput["row_index"], DateChangeInput["new_date"])


# function for statistics printing
def print_stats(item_chosen, days_chosen=None):
    global df
    # filtering by item
    df_temp = df.loc[df.item.isin([item_chosen])]
    # filtering by time
    df_stats = df_temp.copy()
    # setting correct formats to data in csv
    df_stats.loc[:, "time"] = pd.to_datetime(df_temp["time"], format="%y-%m-%d %H:%M")
    df_stats = df_stats.astype({"value": "float64"})
    del df_temp
    # count number of days between first report and today
    if days_chosen:
        date_interval_start = pd.to_datetime('today') - pd.Timedelta(days=days_chosen)
        if date_interval_start > df_stats["time"].min():
            days_touched = int(days_chosen)
            df_stats = df_stats.loc[df_stats["time"] > date_interval_start]
        else:
            days_touched = (pd.to_datetime('today') - df_stats["time"].min()).days
    else:
        days_touched = (pd.to_datetime('today') - df_stats["time"].min()).days
    if item_chosen == "drinks":
        # count summaries by ins (avg is per day)
        df_stats = df_stats.groupby("ins")["value"].agg(["sum", "mean"]).sort_values("sum", ascending=False)
        df_stats["avg"] = (df_stats["sum"] / days_touched).round(2)
        df_stats["per"] = df_stats["sum"].apply(lambda x: 100 * x / df_stats["sum"].sum()).round(1)

        # temporary drink report
        stats_drinks = "[avg per day] - [summary] - [%]"
        for i in range(len(df_stats.index)):
            stats_drinks = "{0}\n{1} - {2} - {3} - {4}".format(stats_drinks, str(df_stats.index[i]),
                                                               str(df_stats["avg"][i]),
                                                               str(df_stats["sum"][i]), str(df_stats["per"][i]))

        return stats_drinks
    elif item_chosen == "sleep":
        # prepare data for the most slept hours histogram
        df_stats["fall_asleep"] = df_stats["time"] - pd.to_timedelta(df_stats["value"], unit="h")
        sleeping_hours = [0 for _ in range(24)]
        for row in range(len(df_stats)):
            # timedelta_range = (df_stats.iloc[row]["time"] - df_stats.iloc[row]["fall_asleep"]) / pd.Timedelta(1, "H")
            for offset_hour in range(int(df_stats.iloc[row]["value"]) + 1):
                if (df_stats.iloc[row]["fall_asleep"] + pd.Timedelta(hours=offset_hour)) < df_stats.iloc[row]["time"]:
                    comp_time = df_stats.iloc[row]["fall_asleep"] + pd.Timedelta(hours=offset_hour + 1)
                    comp_time = comp_time.replace(minute=0).hour
                    sleeping_hours[comp_time] = sleeping_hours[comp_time] + 1

        # count avg sleeping hours by day
        sleeping_hours_avg = df_stats["value"].mean().round(1)

        # creating histogram graph AS TEXT
        unit_l = 25 / max(sleeping_hours)
        sleep_txt = "[avg sleeping hours] = " + str(sleeping_hours_avg) + "\n\nSleeping hours distribution during day:"
        for unit in range(24):
            if len(str(unit)) == 1:
                legend = "0" + str(unit)
            else:
                legend = str(unit)
            sleep_txt = sleep_txt + "\n[" + legend + "] " + str("l" * int(sleeping_hours[unit] * unit_l))

        return sleep_txt
    else:
        return "Не могу обработать такой запрос"


def askPrintStats(message):
    if not re.match("^(?P<item>[^\*]+)([\*]{1})?(?P<days>[^\*]+)?$", message.text):
        msg = bot.send_message(message.chat.id, "❗ Вы ввели некорректное значение, попробуйте еще раз!")
        bot.register_next_step_handler(msg, askPrintStats)
        return
    stats_config = [match.groupdict() for match in
                    re.finditer("^(?P<item>[^\*]+)([\*]{1})?(?P<days>[^\*]+)?$", message.text)]
    item_chosen = stats_config[0]["item"]
    days_chosen = 9999
    if stats_config[0]["days"]:
        days_chosen = int(stats_config[0]["days"])
    bot.send_message(message.chat.id,
                     print_stats(item_chosen, days_chosen),
                     reply_markup=keyboard_menu)


if __name__ == '__main__':
    bot.polling(none_stop=True)
