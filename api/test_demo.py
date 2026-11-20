import unittest
from unittest.mock import patch
from pydantic import ValidationError
from .routers.zeta import SavedProject
from .routers.assistant import Conversation, plan


class DemoContracts(unittest.TestCase):
    def test_record_unknown_field_rejected(self):
        with self.assertRaises(ValidationError):
            SavedProject.model_validate({'app':None,'rows':[{'id':'x','values':{'unknown':'test'}}]})

    def test_duplicate_record_ids_rejected(self):
        with self.assertRaises(ValidationError):
            SavedProject.model_validate({'app':None,'rows':[{'id':'x','values':{}},{'id':'x','values':{}}]})

    def test_plan_requires_checks_before_build(self):
        from fastapi import HTTPException
        with patch('api.routers.assistant.deps.require_password_changed'), patch('api.routers.assistant.complete_json',return_value=('{"ready":true,"reply":"OK","requirement":"create tasks","checks":[]}',{},'test')):
            with self.assertRaises(HTTPException):
                plan(Conversation(messages=[{'role':'user','content':'Create tasks'}]),user=object())
