"""OMML 公式与 md_to_docx 双轨（OMML → PNG）。"""
from __future__ import annotations

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

SHARED_PKG = Path(__file__).resolve().parents[1]
SHARED = SHARED_PKG / "tools"
ROOT = SHARED_PKG.parent.parent if SHARED_PKG.parent.name == "skills" else SHARED_PKG.parent
if str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))


class MathToOmmlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import latex2mathml
        except ImportError:
            raise unittest.SkipTest("latex2mathml not installed")

    def test_latex_to_omml_has_omath(self):
        from lxml import etree
        from math_to_omml import latex_to_omml

        el = latex_to_omml(r"s = \alpha x + \beta y", display=True)
        s = etree.tostring(el, encoding="unicode")
        self.assertIn("oMath", s)

    def test_try_fails_gracefully(self):
        from math_to_omml import try_latex_to_omml

        # 极怪输入仍应返回 None 而非抛错
        self.assertIsNone(try_latex_to_omml(r"\unknownmacro{???{{{"))

    def test_left_right_min_converts(self):
        from lxml import etree
        from math_to_omml import latex_to_omml

        el = latex_to_omml(
            r"\min\left(1,\frac{p_{mem}}{\max(1,d_{mem})}\right)",
            display=True,
        )
        self.assertIn("oMath", etree.tostring(el, encoding="unicode"))

    def test_tag_kept_as_equation_number(self):
        from math_to_omml import normalize_latex_for_omml, try_latex_to_omml
        from lxml import etree

        latex = r"w_{\mathrm{am}} \equiv 1 \tag{1}"
        self.assertIn(r"\quad (1)", normalize_latex_for_omml(latex))
        el = try_latex_to_omml(latex, display=True)
        self.assertIsNotNone(el)
        xml = etree.tostring(el, encoding="unicode")
        self.assertIn("oMath", xml)
        self.assertRegex(xml, r">1<")

    def test_superscript_uses_msup_not_msub(self):
        from lxml import etree
        from math_to_omml import latex_to_omml

        xml = etree.tostring(latex_to_omml(r"x^{2}", display=False), encoding="unicode")
        self.assertIn("<m:sSup", xml)
        self.assertIn("<m:sup", xml)
        self.assertNotIn("<m:sub", xml)

    def test_unknown_unit_macros_become_visible_chars(self):
        from math_to_omml import normalize_latex_for_omml, try_latex_to_omml
        from lxml import etree

        cases = {
            r"70\,\mathrm{^{\circ}F}": "℉",
            r"1.5\,\AA": "Å",
            r"10\,\ohm": "Ω",
            r"5\permil": "‰",
            r"10\,\micro m": "µ",
            r"5\sim 20": "∼",
        }
        for latex, needle in cases.items():
            norm = normalize_latex_for_omml(latex)
            el = try_latex_to_omml(latex, display=False)
            self.assertIsNotNone(el, latex)
            xml = etree.tostring(el, encoding="unicode")
            self.assertIn(needle, xml, f"{latex} norm={norm} xml={xml}")
            self.assertNotIn("\\ohm", xml)
            self.assertNotIn("\\AA", xml)

    def _xml(self, latex: str, *, display: bool = False) -> str:
        from lxml import etree
        from math_to_omml import latex_to_omml

        el = latex_to_omml(latex, display=display)
        return etree.tostring(el, encoding="unicode")

    def test_command_table_all_macros_render(self):
        from math_to_omml import _LATEX_CMD_TO_REPL, normalize_latex_for_omml, try_latex_to_omml
        from lxml import etree

        samples = {
            "perthousand": r"5\perthousand",
            "textcelsius": r"70\textcelsius",
            "textfahrenheit": r"70\textfahrenheit",
            "textdegree": r"30\textdegree",
            "angstrom": r"1.5\angstrom",
            "permil": r"5\permil",
            "degree": r"30\degree",
            "micro": r"10\micro m",
            "ohm": r"10\ohm",
            "AA": r"1.5\AA",
        }
        self.assertEqual({cmd for cmd, _ in _LATEX_CMD_TO_REPL}, set(samples))
        for cmd, needle in _LATEX_CMD_TO_REPL:
            latex = samples[cmd]
            norm = normalize_latex_for_omml(latex)
            self.assertIn(needle, norm, f"{cmd} norm={norm}")
            self.assertNotIn("\\" + cmd, norm, f"{cmd} leftover in norm={norm}")
            el = try_latex_to_omml(latex, display=False)
            self.assertIsNotNone(el, latex)
            xml = etree.tostring(el, encoding="unicode")
            self.assertIn(needle, xml, f"{cmd} xml={xml}")
            self.assertNotIn("\\" + cmd, xml)

    def test_circ_unit_pattern_variants(self):
        from math_to_omml import normalize_latex_for_omml, try_latex_to_omml
        from lxml import etree

        celsius = [
            r"70\,\mathrm{^{\circ}C}",
            r"70\,\mathrm{^\circ C}",
            r"70\,^{\circ}\mathrm{C}",
            r"70\,^\circ\mathrm{C}",
            r"70\,^{\circ}C",
            r"70\,^\circ C",
        ]
        fahrenheit = [r"32\,\mathrm{^{\circ}F}", r"32\,^{\circ}F"]
        kelvin = [r"300\,\mathrm{^{\circ}K}", r"300\,^{\circ}K"]
        for latex in celsius:
            self.assertIn("℃", normalize_latex_for_omml(latex), latex)
            xml = etree.tostring(try_latex_to_omml(latex, display=False), encoding="unicode")
            self.assertIn("℃", xml, latex)
            self.assertNotIn("\u2218", xml)
        for latex in fahrenheit:
            xml = etree.tostring(try_latex_to_omml(latex, display=False), encoding="unicode")
            self.assertIn("℉", xml, latex)
        for latex in kelvin:
            xml = etree.tostring(try_latex_to_omml(latex, display=False), encoding="unicode")
            self.assertIn("°", xml, latex)
            self.assertIn(">K<", xml, latex)
            self.assertNotIn("\u2218", xml)

    def test_bare_degree_superscript_not_ring_operator(self):
        from math_to_omml import normalize_latex_for_omml

        for latex in (r"30^{\circ}", r"30^\circ"):
            norm = normalize_latex_for_omml(latex)
            self.assertIn("°", norm, latex)
            self.assertNotIn(r"\circ", norm)
            xml = self._xml(latex)
            self.assertIn("°", xml)
            self.assertNotIn("\u2218", xml)

    def test_comparison_aliases_and_sim(self):
        from math_to_omml import normalize_latex_for_omml

        self.assertIn(r"\leq", normalize_latex_for_omml(r"a \le b"))
        self.assertIn(r"\geq", normalize_latex_for_omml(r"a \ge b"))
        self.assertIn("∼", normalize_latex_for_omml(r"5\sim 20"))
        xml = self._xml(r"T_{\mathrm{bed}} \ge \tau_{\mathrm{hi}}")
        self.assertIn("oMath", xml)

    def test_empty_base_degree_is_flattened(self):
        xml = self._xml(r"\mathrm{^{\circ}}")
        self.assertIn("°", xml)
        self.assertNotIn("<m:sSup", xml)
        self.assertNotIn("\u2218", xml)

    def test_non_cjk_run_uses_cambria_math(self):
        xml = self._xml(r"x^{2}")
        self.assertIn("Cambria Math", xml)

    def test_cjk_in_formula_keeps_omml(self):
        xml = self._xml(r"开:\ T_{\mathrm{bed}} \ge \tau_{\mathrm{hi}} \tag{3}", display=True)
        self.assertIn("开", xml)
        self.assertIn("oMath", xml)

    def test_celsius_does_not_use_ring_operator_superscript(self):
        from math_to_omml import normalize_latex_for_omml, try_latex_to_omml
        from lxml import etree

        latex = r"\tau_{\mathrm{hi}}=70\,\mathrm{^{\circ}C}"
        norm = normalize_latex_for_omml(latex)
        self.assertIn("℃", norm)
        self.assertNotIn(r"\circ", norm)
        el = try_latex_to_omml(latex, display=False)
        self.assertIsNotNone(el)
        xml = etree.tostring(el, encoding="unicode")
        self.assertIn("℃", xml)
        self.assertNotIn("\u2218", xml)

    def test_score_with_left_right_converts(self):
        from math_to_omml import try_latex_to_omml

        latex = (
            r"Score(\mathbf{d},\mathbf{p}) = w_{cpu}\cdot d_{cpu}\cdot p_{cpu} + "
            r"w_{mem}\cdot \min\left(1,\frac{p_{mem}}{\max(1,d_{mem})}\right) + "
            r"w_{io}\cdot(1-p_{io\_busy})\cdot d_{io} - \lambda\cdot n_{inflight}"
        )
        self.assertIsNotNone(try_latex_to_omml(latex, display=True))


class MdToDocxOmmlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import latex2mathml
            from docx import Document
        except ImportError:
            raise unittest.SkipTest("latex2mathml/python-docx missing")

    def test_block_equation_writes_omml(self):
        from md_to_docx import convert_md_to_docx

        md = "前文\n\n$$\ns = \\alpha x + \\beta y\n$$\n\n后文\n"
        doc = convert_md_to_docx(md, base_dir=None, prefer_omml=True)
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "t.docx"
            doc.save(str(out))
            with zipfile.ZipFile(out) as zf:
                xml = zf.read("word/document.xml").decode("utf-8")
        self.assertIn("oMath", xml)
        self.assertIn("oMathPara", xml)
        from md_to_docx import get_math_stats

        st = get_math_stats()
        self.assertGreaterEqual(st.omml, 1)
        self.assertEqual(st.text, 0)

    def test_single_line_bracket_block_writes_omml(self):
        from md_to_docx import convert_md_to_docx, get_math_stats

        md = (
            "前文\n\n"
            r"\[ w_{\mathrm{am}} \equiv \frac{m_{\mathrm{am}}}{m_{\mathrm{sil}} + m_{\mathrm{am}}} \tag{1} \]"
            "\n\n后文\n"
        )
        doc = convert_md_to_docx(md, base_dir=None, prefer_omml=True)
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "t.docx"
            doc.save(str(out))
            with zipfile.ZipFile(out) as zf:
                xml = zf.read("word/document.xml").decode("utf-8")
        self.assertIn("oMath", xml)
        self.assertNotIn(r"\[", xml)
        st = get_math_stats()
        self.assertGreaterEqual(st.omml, 1)
        self.assertEqual(st.text, 0)

    def test_inline_celsius_uses_degree_celsius_char(self):
        from md_to_docx import convert_md_to_docx

        md = r"取 \(\tau_{\mathrm{hi}}=70\,\mathrm{^{\circ}C}\)。"
        doc = convert_md_to_docx(md, base_dir=None, prefer_omml=True)
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "t.docx"
            doc.save(str(out))
            with zipfile.ZipFile(out) as zf:
                xml = zf.read("word/document.xml").decode("utf-8")
        self.assertIn("℃", xml)
        self.assertNotIn("\u2218", xml)
        self.assertIn("oMath", xml)

    def test_walkthrough_units_and_tagged_equation(self):
        from md_to_docx import convert_md_to_docx, get_math_stats

        md = "\n".join(
            [
                r"数值走查：\(\tau_{\mathrm{hi}}=70\,\mathrm{^{\circ}C}\)、\(5\sim 20\,\mathrm{^{\circ}C}\)、"
                r"\(1.5\,\AA\)、\(10\,\ohm\)、\(5\permil\)。",
                "",
                r"\[ w_{\mathrm{am}} \equiv \frac{m_{\mathrm{am}}}{m_{\mathrm{sil}}} \tag{1} \]",
                "",
            ]
        )
        doc = convert_md_to_docx(md, base_dir=None, prefer_omml=True)
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "t.docx"
            doc.save(str(out))
            with zipfile.ZipFile(out) as zf:
                xml = zf.read("word/document.xml").decode("utf-8")
        st = get_math_stats()
        self.assertEqual(st.text, 0, st.text_latex)
        self.assertGreaterEqual(st.omml, 2)
        self.assertIn("℃", xml)
        self.assertIn("∼", xml)
        self.assertIn("Å", xml)
        self.assertIn("Ω", xml)
        self.assertIn("‰", xml)
        self.assertIn("oMathPara", xml)
        self.assertNotIn("\u2218", xml)
        self.assertNotIn(r"\[", xml)
        from md_to_docx import convert_md_to_docx, get_math_stats

        convert_md_to_docx(
            "$$\n\\unknownmacro{???{{{\n$$\n",
            base_dir=None,
            prefer_omml=True,
        )
        st = get_math_stats()
        self.assertGreaterEqual(st.text, 1)
        self.assertTrue(any("unknownmacro" in x for x in st.text_latex))

    def test_no_omml_falls_back_without_crash(self):
        from md_to_docx import convert_md_to_docx

        md = "$$\na+b\n$$\n"
        doc = convert_md_to_docx(md, base_dir=None, prefer_omml=False)
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "t.docx"
            doc.save(str(out))
            self.assertTrue(out.is_file())


if __name__ == "__main__":
    unittest.main()
