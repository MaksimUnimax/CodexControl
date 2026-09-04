import asyncio
import json
from pathlib import Path
import unittest

from codex_control.adapters.codex.model_catalog import *


def model(*, identifier="record-a", wire="wire-a", name="A", efforts=("low", "high"), default="low", hidden=False, is_default=False, **extra):
    return {"id": identifier, "model": wire, "displayName": name, "description": extra.pop("description", "safe"), "supportedReasoningEfforts":[{"reasoningEffort": x, "description":"ignored"} for x in efforts], "defaultReasoningEffort":default, "hidden":hidden, "isDefault":is_default, **extra}


class Client:
    def __init__(self, pages, gate=None): self.pages, self.calls, self.gate, self.requested = list(pages), [], gate, asyncio.Event()
    async def request(self, method, params):
        self.calls.append((method, dict(params)))
        self.requested.set()
        if self.gate: await self.gate.wait()
        result = self.pages.pop(0)
        if isinstance(result, BaseException): raise result
        return result


class Runtime:
    def __init__(self, profile_id, generation, client): self.profile_id, self.generation, self.client = profile_id, generation, client


class Manager:
    def __init__(self, runtimes): self.runtimes, self.calls, self.acquire_events = runtimes, [], {}
    async def acquire(self, profile_id):
        self.calls.append(profile_id)
        event = self.acquire_events.get(len(self.calls))
        if event is not None: event.set()
        return self.runtimes[profile_id]


class Clock:
    def __init__(self): self.value = 10.0
    def __call__(self): return self.value


class FixtureTests(unittest.TestCase):
    def test_schema_bound_fixture(self):
        raw = json.loads(Path("tests/fixtures/codex_app_server_0_144_6/model_list_protocol.json").read_text())
        self.assertEqual(raw["codex_version"], "0.144.6")
        self.assertEqual(raw["schema_sha256"], "40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466")
        self.assertEqual(raw["model_list_method"], "model/list")
        self.assertEqual(raw["request_parameter_fields"], ["cursor", "includeHidden", "limit"])
        self.assertEqual(raw["response_collection_field"], "data"); self.assertEqual(raw["pagination_cursor_field"], "nextCursor")
        self.assertEqual(raw["normalized_source_fields"], {"model_id":"id", "wire_model":"model", "display_name":"displayName"})
        self.assertEqual(raw["supported_reasoning_effort_source"], {"collection":"supportedReasoningEfforts", "identifier":"reasoningEffort"})
        self.assertEqual(raw["default_reasoning_effort_field"], "defaultReasoningEffort")
        self.assertEqual(raw["default_model_field"], "isDefault"); self.assertEqual(raw["visibility_field"], "hidden")


class CatalogTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.clock = Clock(); self.client = Client([{"data":[model() ], "nextCursor":None}]); self.runtime = Runtime("p", 1, self.client)
        self.manager = Manager({"p":self.runtime}); self.adapter = CodexModelCatalogAdapter(self.manager, clock=self.clock)

    async def test_normalization_request_order_and_selection(self):
        catalog = await self.adapter.get_catalog("p")
        descriptor = catalog.models[0]
        self.assertEqual((descriptor.model_id, descriptor.wire_model, descriptor.display_name), ("record-a", "wire-a", "A"))
        self.assertEqual(descriptor.supported_reasoning_efforts, ("low", "high")); self.assertEqual(descriptor.default_reasoning_effort, "low")
        self.assertEqual(self.client.calls, [("model/list", {"includeHidden":False, "limit":100})])
        self.assertEqual(catalog.resolve_wire_model("record-a"), "wire-a")
        self.assertEqual(catalog.validate_reasoning_effort("record-a", None), "low")
        self.assertEqual(catalog.validate_reasoning_effort("record-a", "high"), "high")
        with self.assertRaisesRegex(ModelCatalogError, "model_not_available"): catalog.resolve_model("A")
        with self.assertRaisesRegex(ModelCatalogError, "reasoning_effort_unsupported"): catalog.validate_reasoning_effort("record-a", "HIGH")

    async def test_pagination_order_hidden_and_default(self):
        self.client.pages = [{"data":[model(identifier="one", wire="w1", name="odd-preview", is_default=True), model(identifier="hidden", wire="wh", hidden=True)], "nextCursor":"next"}, {"data":[model(identifier="two", wire="w2")], "nextCursor":None}]
        catalog = await self.adapter.get_catalog("p")
        self.assertEqual([x.model_id for x in catalog.models], ["one", "two"])
        self.assertTrue(catalog.models[0].is_default)
        self.assertEqual(self.client.calls, [("model/list", {"includeHidden":False,"limit":100}), ("model/list", {"includeHidden":False,"limit":100,"cursor":"next"})])

    async def test_invalid_normalization_is_atomic_and_does_not_leak_description(self):
        self.client.pages = [{"data":[model()], "nextCursor":"x"}, {"data":[model(identifier="", description="PRIVATE_MODEL_TEXT_SHOULD_NOT_LEAK")], "nextCursor":None}]
        with self.assertRaises(ModelCatalogError) as raised: await self.adapter.get_catalog("p")
        self.assertNotIn("PRIVATE_MODEL_TEXT_SHOULD_NOT_LEAK", repr(raised.exception)); self.assertFalse(self.adapter._cache)

    async def test_raw_page_with_exactly_100_items_is_accepted(self):
        self.client.pages = [{"data": [model(identifier=f"id-{index}", wire=f"wire-{index}") for index in range(MAX_MODEL_LIST_PAGE_ITEMS)]}]
        catalog = await self.adapter.get_catalog("p")
        self.assertEqual(len(catalog.models), MAX_MODEL_LIST_PAGE_ITEMS)

    async def test_raw_page_with_101_visible_items_fails_closed_without_cache_or_payload(self):
        payload = "PRIVATE_VISIBLE_MODEL_DESCRIPTION"
        self.client.pages = [{"data": [model(identifier=f"id-{index}", wire=f"wire-{index}", description=payload) for index in range(MAX_MODEL_LIST_PAGE_ITEMS + 1)]}]
        with self.assertRaisesRegex(ModelCatalogError, "catalog_limit_exceeded") as raised:
            await self.adapter.get_catalog("p")
        self.assertNotIn(payload, str(raised.exception) + repr(raised.exception))
        self.assertFalse(self.adapter._cache)

    async def test_raw_page_with_101_hidden_items_fails_closed_without_cache_or_payload(self):
        payload = "PRIVATE_HIDDEN_MODEL_DESCRIPTION"
        self.client.pages = [{"data": [model(identifier=f"hidden-{index}", wire=f"hidden-wire-{index}", hidden=True, description=payload) for index in range(MAX_MODEL_LIST_PAGE_ITEMS + 1)]}]
        with self.assertRaisesRegex(ModelCatalogError, "catalog_limit_exceeded") as raised:
            await self.adapter.get_catalog("p")
        self.assertNotIn(payload, str(raised.exception) + repr(raised.exception))
        self.assertFalse(self.adapter._cache)

    async def test_malformed_cases_and_bounds(self):
        cases = [
            {"data":[model(efforts=("low","low"))]}, {"data":[model(default="bad")]}, {"data":[model(identifier="x"*(MAX_MODEL_ID_CHARS+1))]},
            {"data":[model(wire="x"*(MAX_WIRE_MODEL_CHARS+1))]}, {"data":[model(name="x"*(MAX_MODEL_DISPLAY_NAME_CHARS+1))]},
            {"data":[model(efforts=tuple(str(i) for i in range(MAX_REASONING_EFFORTS_PER_MODEL+1)), default="0")]},
            {"data":[model(efforts=("x"*(MAX_REASONING_EFFORT_CHARS+1),), default="x"*(MAX_REASONING_EFFORT_CHARS+1))]}, {"bad":[]}, {"data":[{}]},
        ]
        for page in cases:
            self.client.pages=[page]
            with self.subTest(page=page):
                with self.assertRaises(ModelCatalogError): await self.adapter.get_catalog("p", refresh=True)

    async def test_duplicates_defaults_cursors_and_limits(self):
        for pages in [
            [{"data":[model(), model(identifier="record-a", wire="other")] }], [{"data":[model(), model(identifier="other", wire="wire-a")]}], [{"data":[model(is_default=True), model(identifier="b", wire="b", is_default=True)]}],
            [{"data":[model()], "nextCursor":"x"}, {"data":[model()], "nextCursor":None}],
            [{"data":[model()], "nextCursor":"x"}, {"data":[model(identifier="b",wire="b")], "nextCursor":"x"}],
            [{"data":[model()], "nextCursor":"x"*(MAX_MODEL_LIST_CURSOR_CHARS+1)}], [{"data":[], "nextCursor":False}],
        ]:
            self.client.pages=pages
            with self.assertRaises(ModelCatalogError): await self.adapter.get_catalog("p", refresh=True)
        self.client.pages=[{"data":[model(identifier=str(i),wire="w"+str(i)) for i in range(MAX_MODEL_CATALOG_SIZE+1)]}]
        with self.assertRaises(ModelCatalogError): await self.adapter.get_catalog("p", refresh=True)
        self.client.pages=[{"data":[],"nextCursor":str(i)} for i in range(MAX_MODEL_LIST_PAGES)]
        with self.assertRaises(ModelCatalogError): await self.adapter.get_catalog("p", refresh=True)

    async def test_cache_ttl_profiles_generations_and_refresh_failure(self):
        first = await self.adapter.get_catalog("p"); self.assertIs(first, await self.adapter.get_catalog("p")); self.assertEqual(len(self.client.calls), 1)
        self.clock.value = first.expires_at; self.client.pages=[{"data":[model(identifier="fresh",wire="fresh")]}]; fresh=await self.adapter.get_catalog("p"); self.assertEqual(fresh.models[0].model_id,"fresh")
        self.client.pages=[RuntimeError("no")]
        with self.assertRaises(RuntimeError): await self.adapter.get_catalog("p", refresh=True)
        self.assertIs(fresh, await self.adapter.get_catalog("p"))
        next_client=Client([{"data":[model(identifier="n",wire="n")]}]); self.runtime=Runtime("p",2,next_client); self.manager.runtimes["p"]=self.runtime
        newer=await self.adapter.get_catalog("p"); self.assertEqual(newer.runtime_generation,2); self.assertNotIn(("p",1),self.adapter._cache)

    async def test_profile_isolation_singleflight_cancellation_and_late_old_result(self):
        gate=asyncio.Event(); client=Client([{"data":[model()]}], gate); old=Runtime("p",1,client); other=Runtime("q",1,Client([{"data":[model(identifier="q",wire="q")]}])); self.manager=Manager({"p":old,"q":other}); self.adapter=CodexModelCatalogAdapter(self.manager,clock=self.clock)
        first=asyncio.create_task(self.adapter.get_catalog("p")); await client.requested.wait()
        second=asyncio.create_task(self.adapter.get_catalog("p",refresh=True)); first.cancel()
        with self.assertRaises(asyncio.CancelledError): await first
        gate.set(); result=await second; self.assertEqual(result.profile_id,"p"); self.assertEqual(len(client.calls),1)
        await self.adapter.get_catalog("q"); self.assertIn(("q",1),self.adapter._cache)
        gate2=asyncio.Event(); old_client=Client([{"data":[model()]}],gate2); self.manager.runtimes["p"]=Runtime("p",1,old_client); old_task=asyncio.create_task(self.adapter.get_catalog("p",refresh=True)); await old_client.requested.wait()
        new_client=Client([{"data":[model(identifier="new",wire="new")]}]); self.manager.runtimes["p"]=Runtime("p",2,new_client); await self.adapter.get_catalog("p"); gate2.set(); await old_task
        self.assertNotIn(("p",1),self.adapter._cache); self.assertIn(("p",2),self.adapter._cache)

    async def test_simultaneous_cache_misses_share_one_refresh(self):
        gate = asyncio.Event()
        client = Client([{"data": [model()]}], gate)
        manager = Manager({"p": Runtime("p", 1, client)})
        fifth_acquire = asyncio.Event()
        manager.acquire_events[5] = fifth_acquire
        self.adapter = CodexModelCatalogAdapter(manager, clock=self.clock)
        callers = [asyncio.create_task(self.adapter.get_catalog("p")) for _ in range(5)]
        await client.requested.wait()
        await fifth_acquire.wait()
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(len(self.adapter._inflight), 1)
        gate.set()
        catalogs = await asyncio.gather(*callers)
        self.assertTrue(all(catalog is catalogs[0] for catalog in catalogs))
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(len(self.adapter._cache), 1)
        self.assertFalse(self.adapter._inflight)

    async def test_simultaneous_forced_refreshes_share_one_refresh(self):
        await self.adapter.get_catalog("p")
        gate = asyncio.Event()
        refreshed_client = Client([{"data": [model(identifier="refreshed", wire="refreshed-wire")]}], gate)
        self.manager.runtimes["p"] = Runtime("p", 1, refreshed_client)
        first = asyncio.create_task(self.adapter.get_catalog("p", refresh=True))
        await refreshed_client.requested.wait()
        second_acquire = asyncio.Event()
        self.manager.acquire_events[3] = second_acquire
        second = asyncio.create_task(self.adapter.get_catalog("p", refresh=True))
        await second_acquire.wait()
        self.assertEqual(len(refreshed_client.calls), 1)
        self.assertEqual(len(self.adapter._inflight), 1)
        gate.set()
        first_catalog, second_catalog = await asyncio.gather(first, second)
        self.assertIs(first_catalog, second_catalog)
        self.assertEqual(first_catalog.models[0].model_id, "refreshed")
        self.assertEqual(len(refreshed_client.calls), 1)
        self.assertFalse(self.adapter._inflight)

    async def test_all_cancelled_waiters_leave_shared_refresh_owned(self):
        gate = asyncio.Event()
        client = Client([{"data": [model()]}], gate)
        manager = Manager({"p": Runtime("p", 1, client)})
        third_acquire = asyncio.Event()
        manager.acquire_events[3] = third_acquire
        self.adapter = CodexModelCatalogAdapter(manager, clock=self.clock)
        callers = [asyncio.create_task(self.adapter.get_catalog("p")) for _ in range(3)]
        await client.requested.wait()
        await third_acquire.wait()
        refresh_task = self.adapter._inflight[("p", 1)]
        for caller in callers:
            caller.cancel()
        for caller in callers:
            with self.assertRaises(asyncio.CancelledError):
                await caller
        self.assertFalse(refresh_task.done())
        self.assertIs(self.adapter._inflight[("p", 1)], refresh_task)
        gate.set()
        completed = await refresh_task
        self.assertIs(self.adapter._cache[("p", 1)], completed)
        self.assertFalse(self.adapter._inflight)
        self.assertIs(completed, await self.adapter.get_catalog("p"))
        self.assertEqual(len(client.calls), 1)

    async def test_failed_cache_miss_clears_inflight_and_later_fetch_succeeds(self):
        self.client.pages = [RuntimeError("read failed")]
        with self.assertRaises(RuntimeError):
            await self.adapter.get_catalog("p")
        self.assertFalse(self.adapter._cache)
        self.assertNotIn(("p", 1), self.adapter._inflight)
        self.client.pages = [{"data": [model(identifier="recovered", wire="recovered-wire")]}]
        catalog = await self.adapter.get_catalog("p")
        self.assertEqual(catalog.models[0].model_id, "recovered")
        self.assertEqual(len(self.client.calls), 2)
        self.assertIs(self.adapter._cache[("p", 1)], catalog)

    async def test_multiple_generations_retain_only_current_profile_cache(self):
        other_client = Client([{"data": [model(identifier="other", wire="other-wire")]}])
        self.manager.runtimes["q"] = Runtime("q", 1, other_client)
        other_catalog = await self.adapter.get_catalog("q")
        for generation in range(1, 6):
            client = Client([{"data": [model(identifier=f"p-{generation}", wire=f"p-wire-{generation}")]}])
            self.manager.runtimes["p"] = Runtime("p", generation, client)
            catalog = await self.adapter.get_catalog("p")
            self.assertEqual(catalog.runtime_generation, generation)
        self.assertEqual(set(key for key in self.adapter._cache if key[0] == "p"), {("p", 5)})
        self.assertFalse([key for key in self.adapter._inflight if key[0] == "p" and key[1] < 5])
        self.assertEqual(self.adapter._observed_generation["p"], 5)
        self.assertIs(self.adapter._cache[("q", 1)], other_catalog)

    async def test_hidden_model_cannot_be_selected(self):
        self.client.pages = [{"data": [model(identifier="visible", wire="visible-wire"), model(identifier="hidden", wire="hidden-wire", hidden=True)]}]
        catalog = await self.adapter.get_catalog("p")
        with self.assertRaisesRegex(ModelCatalogError, "model_not_available"):
            catalog.resolve_model("hidden")
        with self.assertRaisesRegex(ModelCatalogError, "model_not_available"):
            catalog.resolve_wire_model("hidden")

    async def test_model_id_lookup_is_case_sensitive(self):
        self.client.pages = [{"data": [model(identifier="Model-ABC", wire="wire-abc")]}]
        catalog = await self.adapter.get_catalog("p")
        self.assertEqual(catalog.resolve_model("Model-ABC").model_id, "Model-ABC")
        with self.assertRaisesRegex(ModelCatalogError, "model_not_available"):
            catalog.resolve_model("model-abc")
