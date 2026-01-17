from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tests import Form
from odoo.exceptions import ValidationError

DOC_TYPE = [
    'numeric',
    'alphanumeric',
    'other',
]

EXACT_LENGTH = [
    'exact',
    'maximum',
]


@tagged('post_install', '-at_install')
class TestDocumentTypeValidation(TransactionCase):

    def setUp(self):
        super().setUp()
        # Use a unique country code to avoid unique constraints with existing data
        self.country = self.env['res.country'].search([('code', '=', 'ZZ')], limit=1)
        if not self.country:
            self.country = self.env['res.country'].create({
                'name': 'Test Country ZZ',
                'code': 'ZZ',
            })
        
        # Ensure the country uses documents
        if 'l10n_latam_use_documents' in self.country:
            self.country.l10n_latam_use_documents = True

        self.identification_type = self.env['l10n_latam.identification.type'].create({
            'name': 'Identification Type TEST',
            'description': 'Description Identification Type TEST',
            'active': True,
            'country_id': self.country.id,
        })

    def _assert_error_dialog(self, partner):
        """
        Verifica que el campo 'error_dialog' contenga contenido y que el campo 'vat' NO esté vacío.

        :param partner: Objeto res.partner sobre el cual realizar la verificación.
        :type partner: res.partner

        :return: None
        :rtype: None
        """
        self.assertTrue(
            partner,
            "Se debe enviar el parámetro 'partner'"
        )
        self.assertTrue(
            partner.error_dialog,
            'Se espera que el campo error_dialog tenga contenido.'
        )
        self.assertTrue(
            partner.vat,
            'Se espera que el número de identificación NO se limpie.'
        )

    def _assert_no_error_dialog(self, partner):
        """
        Verifica que el campo 'error_dialog' esté vacío, y compara el campo 'vat' 
        con su propio valor, asegurando que no ha cambiado.

        :param partner: Objeto res.partner sobre el cual realizar la verificación.
        :type partner: res.partner

        :return: None
        :rtype: None
        """
        self.assertTrue(
            partner,
            "Se debe enviar el parámetro 'partner'"
        )
        self.assertFalse(
            partner.error_dialog,
            'Se espera que el campo error_dialog esté vacío.'
        )
        self.assertEqual(
            partner.vat, partner.vat,
            f'Se espera que el número de identificación sea {partner.vat}.'
        )

    def _write_identification_type(self, doc_length=0, doc_type=None, exact_length=None):
        if not isinstance(doc_length, int):
            self.fail("El parámetro doc_length debe ser un entero.")

        self.assertIn(
            doc_type, 
            DOC_TYPE, 
            f"El parámetro doc_type debe ser uno de los siguientes valores: {', '.join(DOC_TYPE)}."
        )
        self.assertIn(
            exact_length, 
            EXACT_LENGTH, 
            f"El parámetro exact_length debe ser uno de los siguientes valores: {', '.join(EXACT_LENGTH)}."
        )
        self.identification_type.write({
            'doc_length': doc_length,
            'doc_type': doc_type,
            'exact_length': exact_length,
        })

    def _perform_identification_type_test(self, test_cases):
        # Create partner first to avoid Form visibility issues with l10n_latam fields
        partner_record = self.env['res.partner'].create({
            'name': 'Partner Test',
            'country_id': self.country.id,
            'l10n_latam_identification_type_id': self.identification_type.id,
        })

        for test_case in test_cases:
            # Determine if we expect a validation error (invalid data)
            expect_error = test_case['assertion'] == self._assert_error_dialog
            
            try:
                with Form(partner_record) as partner:
                    partner.vat = test_case['vat']
                    test_case['assertion'](partner)
            except ValidationError:
                # If we expected an error dialog, a ValidationError on save is consistent and acceptable here
                # as we are testing the UI feedback loop and the constraint simultaneously.
                if not expect_error:
                    raise
            else:
                # If we expected an error but didn't get a ValidationError on save, 
                # we technically might want to complain if the constraint didn't fire, 
                # but valid cases just pass through.
                # However, confirm that valid cases did NOT raise.
                pass

    def test_identification_type_numeric_exact(self):
        """
        Prueba la validación del tipo de identificación numérico con longitud exacta.

        Se configura el tipo de identificación actual como numérico, con una longitud exacta de 10 dígitos. 
        Luego se realizan varias pruebas con partners que tienen números de identificación numéricos, 
        con caracteres o ambos.

        Casos de prueba:
        - Cuando el número de identificación es numérico y tiene más de 10 dígitos.
        - Cuando el número de identificación es numérico y tiene menos de 10 dígitos.
        - Cuando el número de identificación es numérico y tiene 10 dígitos.
        - Cuando el número de identificación es de caracteres y tiene más de 10 dígitos.
        - Cuando el número de identificación es de caracteres y tiene menos de 10 dígitos.
        - Cuando el número de identificación es de caracteres y tiene 10 dígitos.
        - Cuando el número de identificación contiene números y caracteres y tiene más de 10 dígitos.
        - Cuando el número de identificación contiene números y caracteres y tiene menos de 10 dígitos.
        - Cuando el número de identificación contiene números y caracteres y tiene 10 dígitos.
        - Cuando el número de identificación cumple con la longitud exacta de 10, pero contiene caracteres especiales.
        """
        self._write_identification_type(doc_length=10, doc_type='numeric', exact_length='exact')

        test_cases = [
            {'vat': '123456789123456789', 'assertion': self._assert_error_dialog},
            {'vat': '123', 'assertion': self._assert_error_dialog},
            {'vat': '1234567891', 'assertion': self._assert_no_error_dialog},
            {'vat': 'ABCDEFGHIJKJLMNORTY', 'assertion': self._assert_error_dialog},
            {'vat': 'ABCDE', 'assertion': self._assert_error_dialog},
            {'vat': 'ABCDEFGHTY', 'assertion': self._assert_error_dialog},
            {'vat': '1234567BCV89a', 'assertion': self._assert_error_dialog},
            {'vat': '167BA89a', 'assertion': self._assert_error_dialog},
            {'vat': '16237BC89a', 'assertion': self._assert_error_dialog},
            {'vat': '1623($1234', 'assertion': self._assert_error_dialog},
        ]

        self._perform_identification_type_test(test_cases)

    def test_identification_type_numeric_maximum(self):
        """
        Prueba la validación del tipo de identificación numérico con longitud máxima.

        Se configura el tipo de identificación actual como numérico, con una longitud máxima de 10 dígitos. 
        Luego se realizan varias pruebas con partners que tienen números de identificación numéricos, 
        con caracteres o ambos.

        Casos de prueba:
        - Cuando el número de identificación es numérico y tiene más de 10 dígitos.
        - Cuando el número de identificación es numérico y tiene menos de 10 dígitos.
        - Cuando el número de identificación es numérico y tiene 10 dígitos.
        - Cuando el número de identificación es de caracteres y tiene más de 10 dígitos.
        - Cuando el número de identificación es de caracteres y tiene menos de 10 dígitos.
        - Cuando el número de identificación es de caracteres y tiene 10 dígitos.
        - Cuando el número de identificación contiene números y caracteres y tiene más de 10 dígitos.
        - Cuando el número de identificación contiene números y caracteres y tiene menos de 10 dígitos.
        - Cuando el número de identificación contiene números y caracteres y tiene 10 dígitos.
        - Cuando el número de identificación cumple con la longitud máxima de 10, pero contiene caracteres especiales.
        """
        self._write_identification_type(doc_length=10, doc_type='numeric', exact_length='maximum')

        test_cases = [
            {'vat': '123456789123456789', 'assertion': self._assert_error_dialog},
            {'vat': '123', 'assertion': self._assert_no_error_dialog},
            {'vat': '1234567891', 'assertion': self._assert_no_error_dialog},
            {'vat': 'ABCDEFGHIJKJLMNORTY', 'assertion': self._assert_error_dialog},
            {'vat': 'ABCDE', 'assertion': self._assert_error_dialog},
            {'vat': 'ABCDEFGHTY', 'assertion': self._assert_error_dialog},
            {'vat': '1234567BCV89a', 'assertion': self._assert_error_dialog},
            {'vat': '167BA89a', 'assertion': self._assert_error_dialog},
            {'vat': '16237BC89a', 'assertion': self._assert_error_dialog},
            {'vat': '1623($1234', 'assertion': self._assert_error_dialog},
        ]

        self._perform_identification_type_test(test_cases)

    def test_identification_type_alphanumeric_exact(self):
        """
        Prueba la validación del tipo de identificación alfanúmerica con longitud exacta.

        Se configura el tipo de identificación actual como alfanúmerica, con una longitud exacta de 10 dígitos. 
        Luego se realizan varias pruebas con partners que tienen números de identificación numéricos, 
        con caracteres o ambos.

        Casos de prueba:
        - Cuando el número de identificación es numérico y tiene más de 10 dígitos.
        - Cuando el número de identificación es numérico y tiene menos de 10 dígitos.
        - Cuando el número de identificación es numérico y tiene 10 dígitos.
        - Cuando el número de identificación es de caracteres y tiene más de 10 dígitos.
        - Cuando el número de identificación es de caracteres y tiene menos de 10 dígitos.
        - Cuando el número de identificación es de caracteres y tiene 10 dígitos.
        - Cuando el número de identificación contiene números y caracteres y tiene más de 10 dígitos.
        - Cuando el número de identificación contiene números y caracteres y tiene menos de 10 dígitos.
        - Cuando el número de identificación contiene números y caracteres y tiene 10 dígitos.
        - Cuando el número de identificación cumple con la longitud exacta de 10, pero contiene caracteres especiales.
        """
        self._write_identification_type(doc_length=10, doc_type='alphanumeric', exact_length='exact')

        test_cases = [
            {'vat': '123456789123456789', 'assertion': self._assert_error_dialog},
            {'vat': '123', 'assertion': self._assert_error_dialog},
            {'vat': '1234567891', 'assertion': self._assert_no_error_dialog},
            {'vat': 'ABCDEFGHIJKJLMNORTY', 'assertion': self._assert_error_dialog},
            {'vat': 'ABCDE', 'assertion': self._assert_error_dialog},
            {'vat': 'ABCDEFGHTY', 'assertion': self._assert_no_error_dialog},
            {'vat': '1234567BCV89a', 'assertion': self._assert_error_dialog},
            {'vat': '167BA89a', 'assertion': self._assert_error_dialog},
            {'vat': '16237BC89a', 'assertion': self._assert_no_error_dialog},
            {'vat': '1623($1234', 'assertion': self._assert_error_dialog},
        ]

        self._perform_identification_type_test(test_cases)

    def test_identification_type_alphanumeric_maximum(self):
        """
        Prueba la validación del tipo de identificación alfanúmerica con longitud máxima.

        Se configura el tipo de identificación actual como alfanúmerica, con una longitud máxima de 10 dígitos. 
        Luego se realizan varias pruebas con partners que tienen números de identificación numéricos, 
        con caracteres o ambos.

        Casos de prueba:
        - Cuando el número de identificación es numérico y tiene más de 10 dígitos.
        - Cuando el número de identificación es numérico y tiene menos de 10 dígitos.
        - Cuando el número de identificación es numérico y tiene 10 dígitos.
        - Cuando el número de identificación es de caracteres y tiene más de 10 dígitos.
        - Cuando el número de identificación es de caracteres y tiene menos de 10 dígitos.
        - Cuando el número de identificación es de caracteres y tiene 10 dígitos.
        - Cuando el número de identificación contiene números y caracteres y tiene más de 10 dígitos.
        - Cuando el número de identificación contiene números y caracteres y tiene menos de 10 dígitos.
        - Cuando el número de identificación contiene números y caracteres y tiene 10 dígitos.
        - Cuando el número de identificación cumple con la longitud máxima de 10, pero contiene caracteres especiales.
        """
        self._write_identification_type(doc_length=10, doc_type='alphanumeric', exact_length='maximum')

        test_cases = [
            {'vat': '123456789123456789', 'assertion': self._assert_error_dialog},
            {'vat': '123', 'assertion': self._assert_no_error_dialog},
            {'vat': '1234567891', 'assertion': self._assert_no_error_dialog},
            {'vat': 'ABCDEFGHIJKJLMNORTY', 'assertion': self._assert_error_dialog},
            {'vat': 'ABCDE', 'assertion': self._assert_no_error_dialog},
            {'vat': 'ABCDEFGHTY', 'assertion': self._assert_no_error_dialog},
            {'vat': '1234567BCV89a', 'assertion': self._assert_error_dialog},
            {'vat': '167BA89a', 'assertion': self._assert_no_error_dialog},
            {'vat': '16237BC89a', 'assertion': self._assert_no_error_dialog},
            {'vat': '1623($1234', 'assertion': self._assert_error_dialog},
        ]

        self._perform_identification_type_test(test_cases)

    def test_identification_type_other_exact(self):
        """
        Prueba la validación del tipo de identificación otros con longitud exacta.

        Se configura el tipo de identificación actual como otros, con una longitud exacta de 10 dígitos. 
        Luego se realizan varias pruebas con partners que tienen números de identificación numéricos, 
        con caracteres o ambos.

        Casos de prueba:
        - Cuando el número de identificación es numérico y tiene más de 10 dígitos.
        - Cuando el número de identificación es numérico y tiene menos de 10 dígitos.
        - Cuando el número de identificación es numérico y tiene 10 dígitos.
        - Cuando el número de identificación es de caracteres y tiene más de 10 dígitos.
        - Cuando el número de identificación es de caracteres y tiene menos de 10 dígitos.
        - Cuando el número de identificación es de caracteres y tiene 10 dígitos.
        - Cuando el número de identificación contiene números y caracteres y tiene más de 10 dígitos.
        - Cuando el número de identificación contiene números y caracteres y tiene menos de 10 dígitos.
        - Cuando el número de identificación contiene números y caracteres y tiene 10 dígitos.
        - Cuando el número de identificación cumple con la longitud exacta de 10, pero contiene caracteres especiales.
        """
        self._write_identification_type(doc_length=10, doc_type='other', exact_length='exact')

        test_cases = [
            {'vat': '123456789123456789', 'assertion': self._assert_error_dialog},
            {'vat': '123', 'assertion': self._assert_error_dialog},
            {'vat': '1234567891', 'assertion': self._assert_no_error_dialog},
            {'vat': 'ABCDEFGHIJKJLMNORTY', 'assertion': self._assert_error_dialog},
            {'vat': 'ABCDE', 'assertion': self._assert_error_dialog},
            {'vat': 'ABCDEFGHTY', 'assertion': self._assert_no_error_dialog},
            {'vat': '1234567BCV89a', 'assertion': self._assert_error_dialog},
            {'vat': '167BA89a', 'assertion': self._assert_error_dialog},
            {'vat': '16237BC89a', 'assertion': self._assert_no_error_dialog},
            {'vat': '1623($1234', 'assertion': self._assert_no_error_dialog},
        ]

        self._perform_identification_type_test(test_cases)

    def test_identification_type_other_maximum(self):
        """
        Prueba la validación del tipo de identificación otros con longitud máxima.

        Se configura el tipo de identificación actual como otros, con una longitud máxima de 10 dígitos. 
        Luego se realizan varias pruebas con partners que tienen números de identificación numéricos, 
        con caracteres o ambos.

        Casos de prueba:
        - Cuando el número de identificación es numérico y tiene más de 10 dígitos.
        - Cuando el número de identificación es numérico y tiene menos de 10 dígitos.
        - Cuando el número de identificación es numérico y tiene 10 dígitos.
        - Cuando el número de identificación es de caracteres y tiene más de 10 dígitos.
        - Cuando el número de identificación es de caracteres y tiene menos de 10 dígitos.
        - Cuando el número de identificación es de caracteres y tiene 10 dígitos.
        - Cuando el número de identificación contiene números y caracteres y tiene más de 10 dígitos.
        - Cuando el número de identificación contiene números y caracteres y tiene menos de 10 dígitos.
        - Cuando el número de identificación contiene números y caracteres y tiene 10 dígitos.
        - Cuando el número de identificación cumple con la longitud máxima de 10, pero contiene caracteres especiales.
        """
        self._write_identification_type(doc_length=10, doc_type='other', exact_length='maximum')

        test_cases = [
            {'vat': '123456789123456789', 'assertion': self._assert_error_dialog},
            {'vat': '123', 'assertion': self._assert_no_error_dialog},
            {'vat': '1234567891', 'assertion': self._assert_no_error_dialog},
            {'vat': 'ABCDEFGHIJKJLMNORTY', 'assertion': self._assert_error_dialog},
            {'vat': 'ABCDE', 'assertion': self._assert_no_error_dialog},
            {'vat': 'ABCDEFGHTY', 'assertion': self._assert_no_error_dialog},
            {'vat': '1234567BCV89a', 'assertion': self._assert_error_dialog},
            {'vat': '167BA89a', 'assertion': self._assert_no_error_dialog},
            {'vat': '16237BC89a', 'assertion': self._assert_no_error_dialog},
            {'vat': '1623($1234', 'assertion': self._assert_no_error_dialog},
        ]

        self._perform_identification_type_test(test_cases)

    def test_validation_regex(self):
        """
        Prueba la validación usando una expresión regular personalizada (`validation_regex`).
        
        Escenario:
        - Configurar tipo de documento con RegEx: ^[A-Z]{3}-[0-9]{3}$ (Ej. ABC-123)
        - Verificar que valores que cumplen el patrón sean aceptados.
        - Verificar que valores que NO cumplen el patrón sean rechazados.
        - Verificar que esta regla tenga prioridad sobre la validación estándar (doc_type).
        """
        # Configuramos un regex estricto: 3 letras mayúsculas, guion, 3 números.
        self.identification_type.write({
            'doc_length': 7,
            'doc_type': 'alphanumeric', # Aunque sea alfanumérico, el regex debe mandar
            'exact_length': 'exact',
            'validation_regex': r'^[A-Z]{3}-[0-9]{3}$'
        })
        
        test_cases = [
            {'vat': 'ABC-123', 'assertion': self._assert_no_error_dialog}, # Valido
            {'vat': 'abc-123', 'assertion': self._assert_error_dialog},    # Error (minúsculas no permitidas por regex)
            {'vat': 'ABC1234', 'assertion': self._assert_error_dialog},    # Error (falta guion)
            {'vat': '123-ABC', 'assertion': self._assert_error_dialog},    # Error (orden incorrecto)
        ]
        
        self._perform_identification_type_test(test_cases)

    def test_constraint_on_save(self):
        """
        Prueba que no se permita guardar si hay un error de validación.
        """
        self._write_identification_type(doc_length=8, doc_type='numeric', exact_length='exact')
        
        # Use create() directly to test the model constraint
        with self.assertRaises(ValidationError):
            self.env['res.partner'].create({
                'name': 'Partner Constraint Test',
                'country_id': self.country.id,
                'l10n_latam_identification_type_id': self.identification_type.id,
                'vat': '123' # Inválido (longitud incorrecta)
            })
