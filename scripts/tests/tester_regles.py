"""Tests de la fonction regles_compatibles(code) sur des cas typés (clé secrète, lecture seule).

Cas : un symptôme du chapitre XVIII ; un cancer ; un code d'une liste (diabète, poussée aiguë, IVG) ; un antécédent Z80-Z99 ;
une pathologie banale ; aucune pathologie ; un code écrit avec un point et en minuscules ; la règle non évaluable jamais renvoyée.

Usage : uv run python -I scripts/tests/tester_regles.py
"""
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent))
from connexion import charger_env, url_postgres  # noqa: E402

RESULTATS = []


def controle(nom, condition, detail=""):
    RESULTATS.append(bool(condition)); print(f"  [{'OK' if condition else 'ÉCHEC'}] {nom}" + (f" — {detail}" if detail else ""))


def main() -> None:
    with psycopg.connect(url_postgres(charger_env())) as cx, cx.cursor() as cur:
        def compat(code):
            cur.execute("select regle, motif from public.regles_compatibles(%s)", (code,)); return dict(cur.fetchall())
        r = compat("R519"); controle("symptôme du chapitre XVIII (R519) : D2 seule", set(r) == {"D2"} and r["D2"] == "chapitre XVIII", str(r))
        r = compat("C504")
        controle("cancer (C504) : D1, D9, SD2, T3, S1-Chronic présentes ; D2, D4, T2-R52, S4, T6, IVG absentes",
                 {"D1", "D9", "SD2", "T3", "S1-Chronic"} <= set(r) and not ({"D2", "D4", "T2-R52", "S4", "T6", "IVG"} & set(r)) and r["D9"] == "chapitre II", str(sorted(r)))
        r = compat("E1190"); controle("diabète (E1190) : T9-diabetes par la liste, D1 par le chapitre IV", r.get("T9-diabetes") == "liste icd_codes_diabetes_chronic" and r.get("D1") == "chapitre IV", str(r.get("T9-diabetes")))
        r = compat("I200"); controle("angor instable (I200) : D6 par la liste des poussées aiguës", r.get("D6") == "liste icd_codes_chronic_attack", str(r.get("D6")))
        r = compat("O0490"); controle("IVG (O0490) : IVG par sa liste, ITG absente", r.get("IVG") == "liste icd_codes_legal_abortion" and "ITG" not in r, str(sorted(r)))
        r = compat("Z851"); controle("antécédent (Z851) : D4 par l'intervalle Z80-Z99, D1 absente", r.get("D4") == "intervalle Z80-Z99" and "D1" not in r, str(sorted(r)))
        r = compat("R5210"); controle("douleur chronique (R5210) : T2-R52 par le code, D2 par le chapitre", r.get("T2-R52") == "code R5210" and "D2" in r, str(sorted(r)))
        r = compat("K409"); controle("pathologie banale (K409) : D1, T3, T8 ; ni D9, ni SD2, ni T9-diabetes", {"D1", "T3", "T8"} <= set(r) and not ({"D9", "SD2", "T9-diabetes"} & set(r)), str(sorted(r)))
        r = compat(None); controle("aucune pathologie (null) : D3-3, T6, T7, S4, S1-Preg ; ni D1, ni D2, ni T3", {"D3-3", "T6", "T7", "S4", "S1-Preg"} <= set(r) and not ({"D1", "D2", "T3"} & set(r)) and all(v == "aucune pathologie principale" for v in r.values()), str(sorted(r)))
        controle("code écrit « c50.4 » : même résultat que C504", compat("c50.4") == compat("C504"))
        controle("code inconnu (X999) : aucune règle", compat("X999") == {})
        # « Aucun ou chapitres I à XVII » : renvoyées pour null ET pour une pathologie de ces chapitres ; « Aucun » seule : pour null seulement
        rn, rk = compat(None), compat("K409")
        controle("« Aucun ou chapitres I à XVII » (D3-1, D3-2, T15, S1-Chronic, S1-Chir, S2, S3) : renvoyées pour null et pour K409",
                 all(c in rn and c in rk for c in ("D3-1", "D3-2", "T15", "S1-Chronic", "S1-Chir", "S2", "S3")) and rk["S2"] == "chapitre XI")
        controle("« Aucun » seule (D3-3, T6, T7, S1-Preg, S1-Postpartum, S4) : renvoyées pour null, pas pour K409 ni C504",
                 all(c in rn and c not in rk and c not in compat("C504") for c in ("D3-3", "T6", "T7", "S1-Preg", "S1-Postpartum", "S4")))
        tout = set(); [tout.update(compat(c)) for c in ("C504", "K409", "R519", None, "E1190", "Z851")]
        controle("la règle non évaluable T10-irradiations n'est jamais renvoyée", "T10-irradiations" not in tout)
    ok, n = sum(RESULTATS), len(RESULTATS); print(f"\nBILAN : {ok} contrôles réussis sur {n}"); sys.exit(0 if ok == n else 1)


if __name__ == "__main__":
    main()
