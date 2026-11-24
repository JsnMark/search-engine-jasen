"""
term_freq.py

Holds formulas for term frequencies
"""
import math

def n_t(term, all_terms):
    """
    n (natural)
    """
    return all_terms.count(term) / len(all_terms)

def l_t(term, all_terms):
    """
    l (log10)
    """
    return 1 + math.log10(n_t(term, all_terms))