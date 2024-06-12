from dataclasses import dataclass
from typing import Optional, TypedDict

import pandas as pd


class Translations(TypedDict):
    """Typed dict containing text that is  display in a speficic language

    Attributes:
        en: English string to display
        nl: Dutch string to display
    """

    en: str
    nl: str


@dataclass
class Translatable:
    """Wrapper class for Translations"""

    translations: Translations

    def toDict(self):
        return self.__dict__.copy()


@dataclass
class PropsUIHeader:
    """Page header

    Attributes:
        title: title of the page
    """

    title: Translatable

    def toDict(self):
        dict = {}
        dict["__type__"] = "PropsUIHeader"
        dict["title"] = self.title.toDict()
        return dict


@dataclass
class PropsUIFooter:
    """Page footer

    Attributes:
        progressPercentage: float indicating the progress in the flow
    """

    def toDict(self):
        dict = {}
        dict["__type__"] = "PropsUIFooter"
        return dict


@dataclass
class PropsUIPromptConfirm:
    """Retry submitting a file page

    Prompt the user if they want to submit a new file.
    This can be used in case a file could not be processed.

    Attributes:
        text: message to display
        ok: message to display if the user wants to try again
        cancel: message to display if the user wants to continue regardless
    """

    text: Translatable
    ok: Translatable
    cancel: Translatable

    def toDict(self):
        dict = {}
        dict["__type__"] = "PropsUIPromptConfirm"
        dict["text"] = self.text.toDict()
        dict["ok"] = self.ok.toDict()
        dict["cancel"] = self.cancel.toDict()
        return dict


@dataclass
class PropsUIPromptConsentFormTable:
    """Table to be shown to the participant prior to donation

    Attributes:
        id: a unique string to itentify the table after donation
        title: title of the table
        data_frame: table to be shown
        visualizations: optional visualizations to be shown. (see TODO for input format)
    """

    id: str
    title: Translatable
    data_frame: pd.DataFrame
    description: Optional[Translatable] = None
    visualizations: Optional[list] = None
    folded: Optional[bool] = False

    def toDict(self):
        dict = {}
        dict["__type__"] = "PropsUIPromptConsentFormTable"
        dict["id"] = self.id
        dict["title"] = self.title.toDict()
        dict["data_frame"] = self.data_frame.to_json()
        dict["description"] = self.description.toDict() if self.description else None
        dict["visualizations"] = self.visualizations if self.visualizations else None
        dict["folded"] = self.folded
        return dict


@dataclass
class PropsUIPromptConsentFormTableE:
    """Table to be shown to the participant prior to donation

    Attributes:
        id: a unique string to itentify the table after donation
        title: title of the table
        data_frame: table to be shown
        visualizations: optional visualizations to be shown. (see TODO for input format)
    """

    id: str
    title: Translatable
    data_frame: str
    description: Optional[Translatable] = None
    visualizations: Optional[list] = None
    folded: Optional[bool] = False

    def toDict(self):
        dict = {}
        dict["__type__"] = "PropsUIPromptConsentFormTable"
        dict["id"] = self.id
        dict["title"] = self.title.toDict()
        dict["data_frame"] = self.data_frame
        dict["description"] = self.description.toDict() if self.description else None
        dict["visualizations"] = self.visualizations if self.visualizations else None
        dict["folded"] = self.folded
        return dict


@dataclass
class PropsUIPromptConsentForm:
    """Tables to be shown to the participant prior to donation

    Attributes:
        tables: a list of tables
        meta_tables: a list of optional tables, for example for logging data
    """

    tables: list[PropsUIPromptConsentFormTable]
    meta_tables: list[PropsUIPromptConsentFormTable]
    description: Optional[Translatable] = None
    donate_question: Optional[Translatable] = None
    donate_button: Optional[Translatable] = None

    def translate_tables(self):
        output = []
        for table in self.tables:
            output.append(table.toDict())
        return output

    def translate_meta_tables(self):
        output = []
        for table in self.meta_tables:
            output.append(table.toDict())
        return output

    def toDict(self):
        dict = {}
        dict["__type__"] = "PropsUIPromptConsentForm"
        dict["tables"] = self.translate_tables()
        dict["metaTables"] = self.translate_meta_tables()
        dict["description"] = self.description and self.description.toDict()
        dict["donateQuestion"] = self.donate_question and self.donate_question.toDict()
        dict["donateButton"] = self.donate_button and self.donate_button.toDict()
        return dict


@dataclass
class PropsUIPromptFileInput:
    """Prompt the user to submit a file

    Attributes:
        description: text with an explanation
        extensions: accepted mime types, example: "application/zip, text/plain"
    """

    description: Translatable
    extensions: str

    def toDict(self):
        dict = {}
        dict["__type__"] = "PropsUIPromptFileInput"
        dict["description"] = self.description.toDict()
        dict["extensions"] = self.extensions
        return dict


class RadioItem(TypedDict):
    """Radio button

    Attributes:
        id: id of radio button
        value: text to be displayed
    """

    id: int
    value: str


@dataclass
class PropsUIPromptRadioInput:
    """Radio group

    This radio group can be used get a mutiple choice answer from a user

    Attributes:
        title: title of the radio group
        description: short description of the radio group
        items: a list of radio buttons
    """

    title: Translatable
    description: Translatable
    items: list[RadioItem]

    def toDict(self):
        dict = {}
        dict["__type__"] = "PropsUIPromptRadioInput"
        dict["title"] = self.title.toDict()
        dict["description"] = self.description.toDict()
        dict["items"] = self.items
        return dict


@dataclass
class PropsUIQuestionOpen:
    """
    NO DOCS YET
    """
    id: int
    question: Translatable

    def toDict(self):
        dict = {}
        dict["__type__"] = "PropsUIQuestionOpen"
        dict["id"] = self.id
        dict["question"] = self.question.toDict()
        return dict


@dataclass
class PropsUIQuestionMultipleChoiceCheckbox:
    """
    NO DOCS YET
    """
    id: int
    question: Translatable
    choices: list[Translatable]

    def toDict(self):
        dict = {}
        dict["__type__"] = "PropsUIQuestionMultipleChoiceCheckbox"
        dict["id"] = self.id
        dict["question"] = self.question.toDict()
        dict["choices"] = [c.toDict() for c in self.choices]
        return dict


@dataclass
class PropsUIQuestionMultipleChoice:
    """
    NO DOCS YET
    """
    id: int
    question: Translatable
    choices: list[Translatable]

    def toDict(self):
        dict = {}
        dict["__type__"] = "PropsUIQuestionMultipleChoice"
        dict["id"] = self.id
        dict["question"] = self.question.toDict()
        dict["choices"] = [c.toDict() for c in self.choices]
        return dict


@dataclass
class PropsUIPromptQuestionnaire:
    """
    NO DOCS YET
    """
    description: Translatable
    questions: list[PropsUIQuestionMultipleChoice | PropsUIQuestionMultipleChoiceCheckbox | PropsUIQuestionOpen]

    def toDict(self):
        dict = {}
        dict["__type__"] = "PropsUIPromptQuestionnaire"
        dict["description"] = self.description.toDict()
        dict["questions"] = [q.toDict() for q in self.questions]
        return dict


@dataclass
class PropsUIPageDonation:
    """A multi-purpose page that gets shown to the user

    Attributes:
        platform: the platform name the user is curently in the process of donating data from
        header: page header
        body: main body of the page, see the individual classes for an explanation
    """

    platform: str
    header: PropsUIHeader
    body: (
        PropsUIPromptRadioInput
        | PropsUIPromptConsentForm
        | PropsUIPromptFileInput
        | PropsUIPromptConfirm
        | PropsUIPromptQuestionnaire
    )
    footer: Optional[PropsUIFooter] = None

    def toDict(self):
        dict = {}
        dict["__type__"] = "PropsUIPageDonation"
        dict["platform"] = self.platform
        dict["header"] = self.header.toDict()
        dict["body"] = self.body.toDict()
        dict["footer"] = self.footer.toDict() if self.footer else None
        return dict


class PropsUIPageEnd:
    """An ending page to show the user they are done"""

    def toDict(self):
        dict = {}
        dict["__type__"] = "PropsUIPageEnd"
        return dict
