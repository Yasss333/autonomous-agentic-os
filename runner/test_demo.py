"""Real Docker checks plus deterministic repair-routing tests; no provider calls."""
import copy
import unittest
from unittest.mock import patch
from . import graph, docker_qa, bundle
from .provider import Completion, Usage


def tool():
    b = graph._fixture_bundle()
    b['tests'].append({'name':'valid_list', 'code':"def run(result, tool):\n    assert isinstance(result['operations'], list)"})
    return b


class DemoChecks(unittest.TestCase):
    def test_docker_rejects_broken_code(self):
        b=tool(); b['source_code']='def handle(input, context):\n    raise ValueError("intentional QA failure")'
        result=docker_qa.run_qa(b,[{}])
        self.assertFalse(result['passed'])
        self.assertIn('intentional QA failure',str(result['failures']))

    def test_docker_accepts_valid_fixture(self):
        result=docker_qa.run_qa(tool(),[{}, {'days':7}])
        self.assertTrue(result['passed'],result)

    def test_real_docker_repair_loop(self):
        import json
        good=tool(); bad=copy.deepcopy(good)
        bad['source_code']='def handle(input, context):\n    raise ValueError("repair me")'
        answers=[bad,good]
        events=[]
        def completion(**kwargs):
            return Completion(json.dumps(answers.pop(0)),Usage('test-only','sponsored',1,1))
        with patch.object(graph.config,'RUNNER_FIXTURE',False), patch.object(graph.provider,'complete',side_effect=completion):
            result=graph.run_workflow({'prompt':'Fixture test', 'api_key':'test-only','payer':'sponsored','usage':[]},lambda k,p:events.append(k))
        self.assertEqual(result['outcome'],'awaiting_activation')
        self.assertEqual(result['attempt'],2)
        self.assertIn('qa_failed',events)
        self.assertIn('repairing',events)
        self.assertIn('qa_passed',events)

    def test_missing_behavior_checks_rejected(self):
        b=tool();b['tests']=[]
        self.assertIn('Include at least two behavioral tests',bundle.validate_bundle(b))

    def test_populated_probe_catches_invalid_operation_shape(self):
        b=tool()
        b['source_code']="def handle(input, context):\n    return {'display':{}, 'operations':[{'create_followup_task':{}} for lead in context.get('snapshot',{}).get('leads',[])]}"
        result=docker_qa.run_qa(b,[{}])
        self.assertFalse(result['passed'])
        self.assertIn('disallowed op',str(result['failures']))


if __name__=='__main__':unittest.main()
