import logging
import json
import io
from typing import Optional, Literal


import pandas as pd

import port.api.props as props
import port.validate as validate
import port.tiktok as tiktok

from port.api.commands import (CommandSystemDonate, CommandUIRender, CommandSystemExit)

LOG_STREAM = io.StringIO()

logging.basicConfig(
    stream=LOG_STREAM,
    level=logging.DEBUG,
    format="%(asctime)s --- %(name)s --- %(levelname)s --- %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S%z",
)

LOGGER = logging.getLogger("script")


def process(session_id):
    LOGGER.info("Starting the donation flow")
    yield donate_logs(f"{session_id}-tracking")

    platforms = [ ("TikTok", extract_tiktok, tiktok.validate), ]

    # For each platform
    # 1. Prompt file extraction loop
    # 2. In case of succes render data on screen
    for platform in platforms:
        platform_name, extraction_fun, validation_fun = platform

        table_list = None

        # Prompt file extraction loop
        while True:
            LOGGER.info("Prompt for file for %s", platform_name)
            yield donate_logs(f"{session_id}-{platform_name}-tracking")

            # vragenlijst
            questionnaire_results = yield render_tiktok_usage_questionnaire()
            if questionnaire_results.__type__ == "PayloadJSON":
                yield donate(f"{session_id}-{platform_name}-tiktok-usage", questionnaire_results.value)
            else:
                LOGGER.info("Skipped tiktok usage questionnaire: %s", platform_name)
                yield donate_logs(f"{session_id}-{platform_name}-tracking")

            # Render the propmt file page
            promptFile = prompt_file("application/zip, text/plain, application/json", platform_name)
            file_result = yield render_donation_page("Selecteer je TikTok bestand", promptFile)

            if file_result.__type__ == "PayloadString":
                validation = validation_fun(file_result.value)

                # DDP is recognized: Status code zero
                if validation.status_code.id == 0: 
                    LOGGER.info("Payload for %s", platform_name)
                    yield donate_logs(f"{session_id}-{platform_name}-tracking")

                    table_list = extraction_fun(file_result.value, validation)
                    break

                # DDP is not recognized: Different status code
                if validation.status_code.id != 0: 
                    LOGGER.info("Not a valid %s zip; No payload; prompt retry_confirmation", platform_name)
                    yield donate_logs(f"{session_id}-{platform_name}-tracking")
                    retry_result = yield render_donation_page("Selecteer je TikTok bestand", retry_confirmation(platform_name))

                    if retry_result.__type__ == "PayloadTrue":
                        continue
                    else:
                        LOGGER.info("Skipped during retry %s", platform_name)
                        yield donate_logs(f"{session_id}-{platform_name}-tracking")
                        break
            else:
                LOGGER.info("Skipped %s", platform_name)
                yield donate_logs(f"{session_id}-{platform_name}-tracking")
                break


        # Render data on screen
        if table_list is not None:
            LOGGER.info("Prompt consent; %s", platform_name)
            yield donate_logs(f"{session_id}-{platform_name}-tracking")

            # Check if something got extracted
            if len(table_list) == 0:
                yield donate_status(f"{session_id}-{platform_name}-NO-DATA-FOUND", "NO_DATA_FOUND")
                table_list.append(create_empty_table(platform_name))

            prompt = assemble_tables_into_form(table_list)
            consent_result = yield render_donation_page("Jouw TikTok gegevens delen", prompt)

            if consent_result.__type__ == "PayloadJSON":
                LOGGER.info("Data donated; %s", platform_name)
                yield donate(platform_name, consent_result.value)
                yield donate_logs(f"{session_id}-{platform_name}-tracking")
                yield donate_status(f"{session_id}-{platform_name}-DONATED", "DONATED")

                questionnaire_results = yield render_questionnaire(platform_name)

                if questionnaire_results.__type__ == "PayloadJSON":
                    yield donate(f"{session_id}-{platform_name}-questionnaire-donation", questionnaire_results.value)
                else:
                    LOGGER.info("Skipped questionnaire: %s", platform_name)
                    yield donate_logs(f"{session_id}-{platform_name}-tracking")

            else:
                LOGGER.info("Skipped ater reviewing consent: %s", platform_name)
                yield donate_logs(f"{session_id}-{platform_name}-tracking")
                yield donate_status(f"{session_id}-{platform_name}-SKIP-REVIEW-CONSENT", "SKIP_REVIEW_CONSENT")

    yield exit(0, "Success")
    yield render_end_page()



##################################################################

def assemble_tables_into_form(table_list: list[props.PropsUIPromptConsentFormTable]) -> props.PropsUIPromptConsentForm:
    """
    Assembles all donated data in consent form to be displayed
    """
    description = props.Translatable(
        {
            "en": """Hieronder vind je je TikTok-gegevens. Wil je ze delen? Klik dan op de knop 'Ja, deel voor onderzoek' onderaan de pagina. Dan kom je op een pagina waar je je bankrekening gegevens kan delen. Wij zorgen dat je je beloning van €15 snel ontvangt.""",
            "nl": """Hieronder vind je je TikTok-gegevens. Wil je ze delen? Klik dan op de knop 'Ja, deel voor onderzoek' onderaan de pagina. Dan kom je op een pagina waar je je bankrekening gegevens kan delen. Wij zorgen dat je je beloning van €15 snel ontvangt."""
        }
    )

    donate_question = props.Translatable({
       "en": "Wil je deze gegevens delen voor onderzoek?",
       "nl": "Wil je deze gegevens delen voor onderzoek?"
    })

    donate_button = props.Translatable({
       "nl": "Ja, deel voor onderzoek",
       "en": "Ja, deel voor onderzoek"
    })

    return props.PropsUIPromptConsentForm(
       table_list, 
       [], 
       description = description,
       donate_question = donate_question,
       donate_button = donate_button
    )




def donate_logs(key):
    log_string = LOG_STREAM.getvalue()  # read the log stream
    if log_string:
        log_data = log_string.split("\n")
    else:
        log_data = ["no logs"]

    return donate(key, json.dumps(log_data))


def create_empty_table(platform_name: str) -> props.PropsUIPromptConsentFormTable:
    """
    Show something in case no data was extracted
    """
    title = props.Translatable({
       "en": "Er ging niks mis, maar we konden geen gegevens in jouw data vinden",
       "nl": "Er ging niks mis, maar we konden geen gegevens in jouw data vinden",
    })
    df = pd.DataFrame(["No data found"], columns=["No data found"])
    table = props.PropsUIPromptConsentFormTable(f"{platform_name}_no_data_found", title, df)
    return table



##################################################################
# Extraction functions


def extract_tiktok(tiktok_file: str, validation) -> list[props.PropsUIPromptConsentFormTable]:
    tables_to_render = []

    df = tiktok.browsing_history_to_df(tiktok_file)
    if not df.empty:
        hours_logged_in = {
            "title": {"en": "Totaal aantal video's gekeken per maand", "nl": "Totaal aantal video's gekeken per maand"},
            "type": "area",
            "group": {
                "column": "Tijdstip",
                "dateFormat": "month"
            },
            "values": [{
                "label": "Aantal"
            }]
        }
        table_title = props.Translatable({"en": "Kijkgeschiedenis", "nl": "Kijkgeschiedenis"})
        table_description = props.Translatable(
            {
                "en": "De tabel hieronder geeft aan welke TikTok video's je precies hebt bekeken en wanneer dat was. De grafiek laat zien hoeveel video's je elke maand hebt bekeken.", 
                "nl": "De tabel hieronder geeft aan welke TikTok video's je precies hebt bekeken en wanneer dat was. De grafiek laat zien hoeveel video's je elke maand hebt bekeken.", 
             }
        )
        table = props.PropsUIPromptConsentFormTable("tiktok_video_browsing_history", table_title, df, table_description, [hours_logged_in]) 
        tables_to_render.append(table)

    df = tiktok.favorite_videos_to_df(tiktok_file)
    if not df.empty:
        table_title = props.Translatable(
            {
                "en": "Favoriete video's", 
                "nl": "Favoriete video's", 
            }
        )
        table_description = props.Translatable(
            {
                "nl": "In de tabel hieronder vind je de video's die tot je favorieten behoren.", 
                "en": "In de tabel hieronder vind je de video's die tot je favorieten behoren.", 
             }
        )
        table = props.PropsUIPromptConsentFormTable("tiktok_favorite_videos", table_title, df, table_description)
        tables_to_render.append(table)


    df = tiktok.favorite_hashtag_to_df(tiktok_file)
    if not df.empty:
        table_title = props.Translatable(
            {
                "en": "Favoriete hashtags", 
                "nl": "Favoriete hashtags", 
            }
        )
        table_description = props.Translatable(
            {
                "en": "In de tabel hieronder vind je de hashtags die tot je favorieten behoren.", 
                "nl": "In de tabel hieronder vind je de hashtags die tot je favorieten behoren.", 
             }
        )
        table = props.PropsUIPromptConsentFormTable("tiktok_favorite_hashtags", table_title, df, table_description)
        tables_to_render.append(table)


    df = tiktok.hashtag_to_df(tiktok_file)
    if not df.empty:
        table_title = props.Translatable(
            {
                "en": "Hashtags in video's die je hebt geplaatst", 
                "nl": "Hashtags in video's die je hebt geplaatst", 
            }
        )
        table_description = props.Translatable(
            {
                "nl": "In de tabel hieronder vind je de hashtags die je gebruikt hebt in een video die je hebt geplaats op TikTok.",
                "en": "In de tabel hieronder vind je de hashtags die je gebruikt hebt in een video die je hebt geplaats op TikTok.",
             }
        )
        table = props.PropsUIPromptConsentFormTable("tiktok_hashtag", table_title, df, table_description)
        tables_to_render.append(table)


    df = tiktok.like_list_to_df(tiktok_file)
    if not df.empty:
        table_title = props.Translatable(
            {
                "en": "Videos die je hebt geliket", 
                "nl": "Videos die je hebt geliket", 
            }
        )
        table_description = props.Translatable(
            {
                "nl": "In de tabel hieronder vind je de video's die je hebt geliket en wanneer dat was.",
                "en": "In de tabel hieronder vind je de video's die je hebt geliket en wanneer dat was.",
             }
        )
        table =  props.PropsUIPromptConsentFormTable("tiktok_like_list", table_title, df, table_description)
        tables_to_render.append(table)


    df = tiktok.searches_to_df(tiktok_file)
    if not df.empty:
        wordcloud = {
            "title": {"en": "", "nl": ""},
            "type": "wordcloud",
            "textColumn": "Zoekterm",
        }
        table_title = props.Translatable(
            {
                "en": "Zoektermen", 
                "nl": "Zoektermen", 
            }
        )
        table_description = props.Translatable(
            {
                "nl": "De tabel hieronder laat zien wat je hebt gezocht en wanneer dat was. De grootte van de woorden in de grafiek geeft aan hoe vaak de zoekterm voorkomt in jouw gegevens.",
                "en": "De tabel hieronder laat zien wat je hebt gezocht en wanneer dat was. De grootte van de woorden in de grafiek geeft aan hoe vaak de zoekterm voorkomt in jouw gegevens.",
             }
        )
        table =  props.PropsUIPromptConsentFormTable("tiktok_searches", table_title, df, table_description, [wordcloud])
        tables_to_render.append(table)


    df = tiktok.share_history_to_df(tiktok_file)
    if not df.empty:
        table_title = props.Translatable(
            {
                "en": "Gedeelde video's", 
                "nl": "Gedeelde video's", 
            }
        )
        table_description = props.Translatable(
            {
                "nl": "In de tabel hieronder vind je wat je hebt gedeeld, op welk tijdstip en de manier waarop.",
                "en": "In de tabel hieronder vind je wat je hebt gedeeld, op welk tijdstip en de manier waarop.",
             }
        )
        table =  props.PropsUIPromptConsentFormTable("tiktok_share_history", table_title, df, table_description)
        tables_to_render.append(table)


    df = tiktok.settings_to_df(tiktok_file)
    if not df.empty:
        table_title = props.Translatable({"en": "Interesses op TikTok", "nl": "Interesses op TikTok"})
        table_description = props.Translatable(
            {
                "nl": "Hieronder vind je de interesses die je hebt aangevinkt bij het aanmaken van je TikTok account",
                "en": "Hieronder vind je de interesses die je hebt aangevinkt bij het aanmaken van je TikTok account",
             }
        )
        table =  props.PropsUIPromptConsentFormTable("tiktok_settings", table_title, df, table_description)
        tables_to_render.append(table)

    return tables_to_render



##########################################

def render_end_page():
    page = props.PropsUIPageEnd()
    return CommandUIRender(page)


def render_donation_page(platform, body):
    header = props.PropsUIHeader(props.Translatable({"en": platform, "nl": platform}))
    footer = props.PropsUIFooter()
    page = props.PropsUIPageDonation(platform, header, body, footer)
    return CommandUIRender(page)


def retry_confirmation(platform):
    text = props.Translatable(
        {
            "en": f"Unfortunately, we could not process your {platform} file. If you are sure that you selected the correct file, press Continue. To select a different file, press Try again.",
            "nl": f"Helaas, kunnen we uw {platform} bestand niet verwerken. Weet u zeker dat u het juiste bestand heeft gekozen? Ga dan verder. Probeer opnieuw als u een ander bestand wilt kiezen."
        }
    )
    ok = props.Translatable({"en": "Try again", "nl": "Probeer opnieuw"})
    cancel = props.Translatable({"en": "Continue", "nl": "Verder"})
    return props.PropsUIPromptConfirm(text, ok, cancel)


def prompt_file(extensions, platform):
    description = props.Translatable(
        {
            "en": f"Kies het bestand dat je opgeslagen hebt op jouw apparaat.",
            "nl": f"Kies het bestand dat je opgeslagen hebt op jouw apparaat."
        }
    )
    return props.PropsUIPromptFileInput(description, extensions)


def donate(key, json_string):
    return CommandSystemDonate(key, json_string)


def exit(code, info):
    return CommandSystemExit(code, info)


def donate_status(filename: str, message: str):
    return donate(filename, json.dumps({"status": message}))

###############################################################################################
# Questionnaire questions

def render_questionnaire(platform_name):

    rekeningnummer = props.Translatable({
        "en": "Rekeningnummer",
        "nl": "Rekeningnummer"
    })

    tenname = props.Translatable({
        "en": "Ten name van",
        "nl": "Ten name van"
    })

    questions = [
        props.PropsUIQuestionOpen(question=rekeningnummer, id=1),
        props.PropsUIQuestionOpen(question=tenname, id=2),
    ]

    description = props.Translatable(
        {
         "en": "Als beloning voor je deelname ontvang je 15 euro. Dit maken we over op je bankrekening, laat je rekeningnummer en je naam achter zodat we het geld over kunnen maken.", 
         "nl": "Als beloning voor je deelname ontvang je 15 euro. Dit maken we over op je bankrekening, laat je rekeningnummer en je naam achter zodat we het geld over kunnen maken.", 
        })
    header = props.PropsUIHeader(props.Translatable({"en": "Dankjewel voor het meedoen!", "nl": "Dankjewel voor het meedoen!"}))
    body = props.PropsUIPromptQuestionnaire(questions=questions, description=description)
    footer = props.PropsUIFooter()

    page = props.PropsUIPageDonation("page", header, body, footer)
    return CommandUIRender(page)



def render_tiktok_usage_questionnaire():

    question = props.Translatable({
        "en": "Hoelang zit je al op TikTok?",
        "nl": "Hoelang zit je al op TikTok?"
    })

    choices = [
        props.Translatable({"en": "Langer dan 2 jaar", "nl": "Langer dan 2 jaar"}),
        props.Translatable({"en": "Tussen 1 en 2 jaar", "nl": "Tussen 1 en 2 jaar"}),
        props.Translatable({"en": "Tussen een half jaar en 1 jaar", "nl": "Tussen een half jaar en 1 jaar"}),
        props.Translatable({"en": "Tussen 1 maand en een half jaar", "nl": "Tussen 1 maand en een half jaar"}),
        props.Translatable({"en": "Korter dan 1 maand", "nl": "Korter dan 1 maand"}),
    ]

    questions = [
        props.PropsUIQuestionMultipleChoice(question=question, choices=choices, id=1),
    ]

    description = props.Translatable(
        {
         "en": "", 
         "nl": "", 
        })
    header = props.PropsUIHeader(props.Translatable({"en": "", "nl": ""}))
    body = props.PropsUIPromptQuestionnaire(questions=questions, description=description)
    footer = props.PropsUIFooter()

    page = props.PropsUIPageDonation("page", header, body, footer)
    return CommandUIRender(page)

