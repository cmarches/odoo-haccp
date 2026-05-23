{
    'name': 'Rapport HACCP DDPP — Community Edition',
    'version': '19.0.1.0.0',
    'summary': 'Variante CE du module HACCP DDPP (OCA quality_control_oca)',
    'category': 'Quality',
    'author': 'AIFluence Digital',
    'depends': ['haccp_report', 'quality_control_oca', 'web', 'mail'],
    # NOTE: groupes OCA présumés depuis branche 18.0 — à vérifier sur 19.0
    'data': [
        'security/ir.model.access.csv',
        'views/menu_override.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'OPL-1',
}
