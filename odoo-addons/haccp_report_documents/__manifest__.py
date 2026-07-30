{
    'name': 'Rapport HACCP — Documents (Enterprise)',
    'version': '19.0.1.0.0',
    'summary': 'Centralise Rapports HACCP, Bibliothèque et formations dans l\'app Documents',
    'category': 'Quality',
    'author': 'AIFluence Digital',
    'depends': ['haccp_report', 'documents'],
    'data': [
        'security/haccp_gerant_security.xml',
        'security/ir.model.access.csv',
        'data/documents_folders.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'OPL-1',
}
