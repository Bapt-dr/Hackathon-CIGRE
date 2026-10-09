"""
Batterie 2h : charge 13h–14h, décharge 20h–21h, avec impact du parc français sur les prix.

Usage :
    python charge_fixe_20h.py donnees_6_avril_2025.csv
"""
import sys
import numpy as np
import pandas as pd

# ---------------- Paramètres ----------------
P_BAT = 200.0            # puissance batterie étudiée (MW)
P_FR = 1300.0            # puissance parc français (MW)
ETA = 0.85               # rendement aller-retour
CHARGE_HOURS = [13, 14]  # charge 13h–14h, quel que soit le prix
DISCHARGE_HOURS = [20, 21]  # décharge 20h–21h


def load(csv_path):
    df = pd.read_csv(csv_path, sep=";", decimal=",", encoding="utf-8-sig")
    df.columns = ["heure", "prix", "solaire", "eolien", "conso", "nuc"]
    prix = df["prix"].to_numpy(dtype=float)
    wind_solar = (df["solaire"] + df["eolien"]).to_numpy(dtype=float)
    return prix, wind_solar


def regression(prix, wind_solar):
    """Pente a et ordonnée b de prix = a·(solaire+éolien) + b, heures à prix négatif."""
    neg = prix < 0
    a, b = np.polyfit(wind_solar[neg], prix[neg], 1)
    return a, b


def schedule(P, eta):
    """
    Profil de puissance (MW) sur 24 h : + charge réseau, − injection réseau.
    - Charge : P MW à 13h et 14h.
    - Décharge : toute l'énergie stockée (η·P·2 MWh), répartie à parts égales sur 20h et 21h.
    """
    profil = np.zeros(24)
    if P <= 0:
        return profil
    for h in CHARGE_HOURS:
        profil[h] = P
    par_heure = eta * P * len(CHARGE_HOURS) / len(DISCHARGE_HOURS)
    for h in DISCHARGE_HOURS:
        profil[h] = -par_heure
    return profil


def revenu(prix, profil):
    """Revenu en € sur la journée (charge = coût si prix > 0, gain si prix < 0)."""
    return -np.sum(prix * profil)


def main(csv_path):
    prix, ws = load(csv_path)
    a, b = regression(prix, ws)
    print(f"Régression : a = {a:.6f}, b = {b:.2f}")

    # Parc FR (même stratégie) et impact sur les prix : Δprix = −a × puissance
    profil_fr = schedule(P_FR, ETA)
    prix_fr = prix - a * profil_fr

    # Batterie étudiée, avant et après impact du parc FR
    profil_bat = schedule(P_BAT, ETA)
    rev_avant = revenu(prix, profil_bat)
    rev_apres = revenu(prix_fr, profil_bat)

    print(f"Charge 13h–14h : {prix[13]:.2f} / {prix[14]:.2f} €/MWh")
    print(f"Décharge 20h–21h : {prix[20]:.2f} / {prix[21]:.2f} €/MWh")
    print(f"Revenu batterie sans parc FR : {rev_avant:,.0f} €/jour")
    print(f"Revenu batterie avec parc FR : {rev_apres:,.0f} €/jour")
    print(f"Impact : {rev_apres - rev_avant:+,.0f} €/jour")
    print(f"Revenu parc FR : {revenu(prix_fr, profil_fr):,.0f} €/jour")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage : python charge_fixe_20h.py donnees_6_avril_2025.csv")
        sys.exit(1)
    main(sys.argv[1])
