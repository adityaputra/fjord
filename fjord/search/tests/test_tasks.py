from nose.tools import eq_

from fjord.feedback.models import ResponseMappingType
from fjord.feedback.tests import response
from fjord.search.index import get_index
from fjord.search.models import Record
from fjord.search.tasks import index_chunk_task
from fjord.search.tests import record, ElasticTestCase


class IndexChunkTaskTest(ElasticTestCase):
    def test_index_chunk_task(self):
        responses = [response(save=True) for i in range(10)]

        # With live indexing, that'll create items in the index. Since
        # we want to test index_chunk_test, we need a clean index to
        # start with so we delete and recreate it.
        self.setup_indexes(empty=True)

        # Verify there's nothing in the index.
        eq_(len(ResponseMappingType.search()), 0)

        # Create the record and the chunk and then run it through
        # celery.
        batch_id = 'ou812'
        rec = record(batch_id=batch_id, save=True)

        chunk = (ResponseMappingType, [item.id for item in responses])
        index_chunk_task.delay(get_index(), batch_id, rec.id, chunk)

        ResponseMappingType.refresh_index()

        # Verify everything is in the index now.
        eq_(len(ResponseMappingType.search()), 10)

        # Verify the record was marked succeeded.
        rec = Record.objects.get(pk=rec.id)
        eq_(rec.status, Record.STATUS_SUCCESS)
