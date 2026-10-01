/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useEffect } from "@odoo/owl";
import { CharField, charField } from "@web/views/fields/char/char_field";

// Aplica una máscara a un texto: "0" es un dígito, cualquier otro símbolo es fijo.
// Ejemplo: aplicarMascara("066895694", "00000000-0") -> "06689569-4"
function aplicarMascara(texto, mascara) {
    const digitos = texto.replace(/\D/g, "");
    let resultado = "";
    let pos = 0;
    for (const simbolo of mascara) {
        if (pos >= digitos.length) {
            break;
        }
        if (simbolo === "0") {
            resultado += digitos[pos++];
        } else {
            resultado += simbolo;
        }
    }
    return resultado;
}

// Campo de texto con máscara mientras se escribe. Uso: widget="masked_char" options="{'mask': '0000-0000'}"
class MaskedCharField extends CharField {
    static props = {
        ...CharField.props,
        mask: { type: String, optional: true },
    };

    setup() {
        super.setup();
        // Reformatea el texto cada vez que el usuario escribe
        useEffect(
            (input) => {
                if (!input || !this.props.mask) {
                    return;
                }
                const alEscribir = () => {
                    input.value = aplicarMascara(input.value, this.props.mask);
                };
                input.addEventListener("input", alEscribir);
                return () => input.removeEventListener("input", alEscribir);
            },
            () => [this.input.el]
        );
    }
}

registry.category("fields").add("masked_char", {
    ...charField,
    component: MaskedCharField,
    extractProps: (fieldInfo) => ({
        ...charField.extractProps(fieldInfo),
        mask: fieldInfo.options.mask,
    }),
});
