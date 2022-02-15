import unittest
from random import choice, randint
from itertools import product

import circuitgraph as cg


class TestProps(unittest.TestCase):
    def setUp(self):
        self.s27 = cg.tx.strip_blackboxes(cg.from_lib("s27"))

    def test_cg_props_avg_sensitivity(self):
        c = cg.Circuit()
        c.add("and", "and")
        c.add("in0", "input", fanout="and")
        c.add("in1", "input", fanout="and")
        self.assertEqual(cg.props.avg_sensitivity(c, "and", approx=False), 1.0)

        avg_sen = cg.props.avg_sensitivity(self.s27, "G17", approx=False)

        # get startpoints of node
        avg_sen_comp = 0
        n = "G17"
        sp = self.s27.startpoints(n)
        for s in sp:
            # compute influence
            infl = 0
            for vs in product([False, True], repeat=len(sp)):
                asmp = {i: v for i, v in zip(sp, vs)}
                asmp_ns = {i: v if i != s else not v for i, v in zip(sp, vs)}
                r = cg.sat.solve(self.s27, asmp)[n]
                r_ns = cg.sat.solve(self.s27, asmp_ns)[n]
                if r != r_ns:
                    infl += 1
            avg_sen_comp += infl / (2 ** len(sp))

        self.assertEqual(avg_sen, avg_sen_comp)

    def test_sensitivity(self):
        # pick random node and input value
        n = choice(tuple(self.s27.nodes()))
        sp = self.s27.startpoints(n)
        while len(sp) < 1:
            n = choice(tuple(self.s27.nodes()))
            sp = self.s27.startpoints(n)

        # find sensitivity
        sen = cg.props.sensitivity(self.s27, n)

        # check
        sen_sim = 0
        for vs in product([False, True], repeat=len(sp)):
            input_sen = 0
            input_val = {i: v for i, v in zip(sp, vs)}
            n_val = cg.sat.solve(self.s27, input_val)[n]
            for s in sp:
                flip_input_val = {i: v if i != s else not v for i, v in zip(sp, vs)}
                flip_n_val = cg.sat.solve(self.s27, flip_input_val)[n]
                if flip_n_val != n_val:
                    input_sen += 1
            sen_sim = max(sen_sim, input_sen)

        self.assertEqual(sen, sen_sim)

    def test_sensitize(self):
        # pick random node
        nr = choice(
            tuple(self.s27.nodes() - set(["clk"]) - self.s27.filter_type(["0", "1"]))
        )

        # pick startpoint
        ns = choice(tuple(self.s27.startpoints() - set(["clk"])))

        # pick endpoint
        ne = choice(tuple(self.s27.endpoints() - set(["clk"])))

        for n in [nr, ns, ne]:
            # get input
            input_val = cg.props.sensitize(self.s27, n, {f"c0_{n}": True})

            # simulate input
            result = cg.sat.solve(self.s27, input_val)
            self.assertTrue(result[n])

            # remove constrained input
            if n in input_val:
                input_val.pop(n)

            # simulate on faulty circuit
            c_f = self.s27.copy()
            c_f.disconnect(c_f.fanin(n), n)
            c_f.set_type(n, "input")
            result_f = cg.sat.solve(c_f, {**input_val, n: False})
            self.assertFalse(result_f[n])
            self.assertTrue(
                any(result_f[e] != result[e] for e in self.s27.endpoints(n))
            )

    def test_signal_probability(self):
        # pick random node
        n = choice(
            tuple(self.s27.nodes() - self.s27.startpoints() - self.s27.endpoints())
        )
        sp = self.s27.startpoints(n)

        # get signal prob
        p = cg.props.signal_probability(self.s27, n, approx=False)

        # compute prob
        m = 0
        for vs in product([False, True], repeat=len(sp)):
            asmp = {i: v for i, v in zip(sp, vs)}
            m += cg.sat.solve(self.s27, asmp)[n]
        self.assertEqual(m / (2 ** len(sp)), p)