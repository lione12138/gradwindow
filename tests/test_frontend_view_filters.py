import json
import shutil
import subprocess
from pathlib import Path


def test_shared_filters_preserve_scope_and_separate_trust_from_time() -> None:
    module_uri = (Path(__file__).parents[1] / "web/view-filters.js").as_uri()
    script = """
      import { readViewFilters, writeViewFilters, matchesDateAndScope,
        matchesTimeStatus } from MODULE;
      const filters = readViewFilters('?q=Data&ranking=the&region=Asia&intake=fall:2027&applicant=international&deadline=30&dates=review&status=closed&sort=deadline&rank=50&saved=1');
      const roundtrip = readViewFilters(writeViewFilters(filters).toString());
      const today = new Date('2026-09-13T00:00:00Z');
      const record = {region:'Asia', intake:'Fall 2027',
        applicantCategories:['international'], opensAt:'2026-09-01',
        closesAt:'2026-09-30', dataStatus:'official', trustStatus:'current'};
      const defaults = readViewFilters('');
      const match = (change, type='official') => matchesDateAndScope(
        {...record, ...change}, {...defaults, dateType:type}, today);
      console.log(JSON.stringify({filters, roundtrip,
        invalid:readViewFilters('?dates=bad&ranking=bad&status=bad'),
        official:match({}), predicted:match({dataStatus:'predicted'}),
        review:match({trustStatus:'needs_review'}),
        explicitReview:match({trustStatus:'needs_review'}, 'review'),
        explicitEstimate:match({dataStatus:'predicted'}, 'estimated'),
        wrongAudience:matchesDateAndScope(record, {...defaults, applicantCategory:'domestic'}, today),
        beforeDeadline:matchesDateAndScope({...record, closesAt:'2026-09-13', deadlineSemantics:'before'}, {...defaults, deadlineRange:'30'}, today),
        open:matchesTimeStatus(record,'open',today),
        closed:matchesTimeStatus(record,'closed',today),
        all:matchesTimeStatus(record,'all',today)
      }));
    """.replace("MODULE", json.dumps(module_uri))
    result = subprocess.run(
        [shutil.which("node"), "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    output = json.loads(result.stdout)
    assert output["roundtrip"] == output["filters"]
    assert output["filters"]["favoritesOnly"] is True
    assert output["invalid"]["dateType"] == "official"
    assert output["invalid"]["ranking"] == "qs"
    assert output["invalid"]["status"] == "open"
    for key in ("official", "explicitReview", "explicitEstimate", "open", "all"):
        assert output[key] is True
    for key in ("predicted", "review", "wrongAudience", "beforeDeadline", "closed"):
        assert output[key] is False
