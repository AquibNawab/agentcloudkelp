from __future__ import annotations

from xml.etree.ElementTree import Element, SubElement, tostring


class JUnitReporter:
    def report(self, result) -> str:
        tests = sum(len(scenario.steps) for scenario in result.scenarios)
        failures = sum(1 for scenario in result.scenarios if not scenario.passed)
        suite = Element("testsuite", name=result.contract_name, tests=str(tests), failures=str(failures))
        for scenario in result.scenarios:
            case = SubElement(suite, "testcase", name=scenario.scenario_name, classname=result.contract_name)
            if not scenario.passed:
                failure = SubElement(case, "failure", message=scenario.failure_reason or "failed")
                failure.text = scenario.failure_reason or "failed"
        return tostring(suite, encoding="unicode")
