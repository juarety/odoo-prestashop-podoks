import requests
from odoo import models, api, fields

PS_IP = "http://prestashop:80"
PS_KEY = "9BD4XS8X7IJASRI412JST3EIIBT43RKP"
PS_HEADERS = {"Host": "localhost:8080"}


class PrestashopSync(models.Model):
    _name = "prestashop.sync"
    _description = "Sincronización con PrestaShop"

    def _ps_request(self, method, path, **kwargs):
        url = f"{PS_IP}/api{path}"
        extra_headers = kwargs.pop("headers", {})
        merged_headers = {**PS_HEADERS, **extra_headers}
        resp = requests.request(
            method,
            url,
            auth=(PS_KEY, ""),
            headers=merged_headers,
            allow_redirects=False,
            **kwargs,
        )
        if resp.status_code in (301, 302):
            new_url = resp.headers["Location"].replace(
                "http://localhost:8080", "http://prestashop:80"
            )
            resp = requests.request(
                method,
                new_url,
                auth=(PS_KEY, ""),
                headers=merged_headers,
                allow_redirects=False,
                **kwargs,
            )
        return resp

    @api.model
    def sync_products(self):
        resp = self._ps_request(
            "GET", "/products", params={"output_format": "JSON", "display": "full"}
        )
        products = resp.json().get("products", [])
        for ps_product in products:
            name = ps_product.get("name", "Sin nombre")
            price = float(ps_product.get("price", 0))
            ps_id = str(ps_product.get("id", ""))

            existing = self.env["product.template"].search(
                ["|", ("x_prestashop_id", "=", ps_id), ("name", "=", name)], limit=1
            )
            if existing:
                if not existing.x_prestashop_id:
                    existing.write({"x_prestashop_id": ps_id})
            else:
                self.env["product.template"].create(
                    {
                        "name": name,
                        "list_price": price,
                        "x_prestashop_id": ps_id,
                    }
                )
        return True

    def _push_product_to_prestashop(self, product):
        xml_data = f"""<?xml version="1.0" encoding="UTF-8"?>
            <prestashop xmlns:xlink="http://www.w3.org/1999/xlink">
            <product>
                <active>1</active>
                <state>1</state>
                <price>{product.list_price:.6f}</price>
                <n>
                <language id="1"><![CDATA[{product.name}]]></language>
                </n>
                <description>
                <language id="1"><![CDATA[]]></language>
                </description>
                <description_short>
                <language id="1"><![CDATA[]]></language>
                </description_short>
                <link_rewrite>
                <language id="1"><![CDATA[{product.name.lower().replace(' ', '-')}]]></language>
                </link_rewrite>
            </product>
            </prestashop>"""
        resp = self._ps_request(
            "POST",
            "/products",
            headers={"Content-Type": "application/xml"},
            data=xml_data.encode("utf-8"),
        )
        if resp.status_code == 201:
            import xml.etree.ElementTree as ET

            try:
                root = ET.fromstring(resp.text)
                ps_id = root.find(".//product/id").text
                product.write({"x_prestashop_id": ps_id})
            except Exception:
                pass
        return resp.status_code

    @api.model
    def push_odoo_products(self):
        resp = self._ps_request(
            "GET", "/products", params={"output_format": "JSON", "display": "full"}
        )
        result = resp.json()
        ps_names = set()
        if isinstance(result, dict) and result.get("products"):
            for p in result["products"]:
                ps_names.add(p.get("name", "").lower().strip())

        odoo_products = self.env["product.template"].search(
            [("x_prestashop_id", "=", False)]
        )
        for product in odoo_products:
            if product.name.lower().strip() in ps_names:
                continue
            status = self._push_product_to_prestashop(product)
            print(f"'{product.name}': {status}")
        return True

    @api.model
    def pull_stock_from_prestashop(self):
        products = self.env["product.template"].search(
            [("x_prestashop_id", "!=", False)]
        )
        for product in products:
            ps_id = product.x_prestashop_id
            resp = self._ps_request(
                "GET",
                "/stock_availables",
                params={
                    "output_format": "JSON",
                    "display": "full",
                    "filter[id_product]": ps_id,
                    "filter[id_product_attribute]": "0",
                },
            )
            result = resp.json()
            if not isinstance(result, dict) or not result.get("stock_availables"):
                continue
            ps_qty = int(result["stock_availables"][0]["quantity"])
            odoo_qty = int(product.qty_available)
            last_known = product.x_prestashop_stock or 0

            if ps_qty < last_known:
                diff = last_known - ps_qty
                product_product = self.env["product.product"].search(
                    [("product_tmpl_id", "=", product.id)], limit=1
                )
                if not product_product:
                    continue
                inventory = self.env["stock.quant"].search(
                    [
                        ("product_id", "=", product_product.id),
                        ("location_id.usage", "=", "internal"),
                    ],
                    limit=1,
                )
                if inventory:
                    new_qty = max(0, inventory.quantity - diff)
                    inventory.sudo().write({"inventory_quantity": new_qty})
                    inventory.sudo().action_apply_inventory()
                    print(f"Venta PS detectada '{product.name}': -{diff} uds")

            product.write({"x_prestashop_stock": ps_qty})
        return True

    @api.model
    def push_stock_to_prestashop(self):
        products = self.env["product.template"].search(
            [("x_prestashop_id", "!=", False)]
        )

        for product in products:
            ps_id = product.x_prestashop_id
            odoo_qty = int(product.qty_available)

            resp = self._ps_request(
                "GET",
                "/stock_availables",
                params={
                    "output_format": "JSON",
                    "display": "full",
                    "filter[id_product]": ps_id,
                    "filter[id_product_attribute]": "0",
                },
            )

            result = resp.json()
            if not isinstance(result, dict) or not result.get("stock_availables"):
                continue

            stock_data = result["stock_availables"][0]
            stock_id = stock_data["id"]

            xml_data = f"""<?xml version="1.0" encoding="UTF-8"?>
                <prestashop xmlns:xlink="http://www.w3.org/1999/xlink">
                <stock_available>
                    <id>{stock_id}</id>
                    <id_product>{ps_id}</id_product>
                    <id_product_attribute>0</id_product_attribute>
                    <id_shop>{stock_data['id_shop']}</id_shop>
                    <id_shop_group>{stock_data['id_shop_group']}</id_shop_group>
                    <quantity>{odoo_qty}</quantity>
                    <depends_on_stock>{stock_data['depends_on_stock']}</depends_on_stock>
                    <out_of_stock>{stock_data['out_of_stock']}</out_of_stock>
                </stock_available>
                </prestashop>"""

            resp = self._ps_request(
                "PUT",
                f"/stock_availables/{stock_id}",
                headers={"Content-Type": "application/xml"},
                data=xml_data.encode("utf-8"),
            )
            print(
                f"Stock '{product.name}': {odoo_qty} uds → PS status {resp.status_code}"
            )
        return True

    @api.model
    def sync_orders(self):
        resp = self._ps_request(
            "GET",
            "/orders",
            params={
                "output_format": "JSON",
                "display": "full",
                "sort": "[id_DESC]",
                "limit": "50",
            },
        )
        result = resp.json()
        if not isinstance(result, dict) or not result.get("orders"):
            return True

        for ps_order in result["orders"]:
            ps_order_id = str(ps_order.get("id"))

            existing = self.env["sale.order"].search(
                [("x_prestashop_order_id", "=", ps_order_id)], limit=1
            )
            if existing:
                continue

            ps_customer_id = str(ps_order.get("id_customer", "0"))
            partner = self.env["res.partner"].search(
                [("x_prestashop_customer_id", "=", ps_customer_id)], limit=1
            )

            if not partner:
                customer_resp = self._ps_request(
                    "GET",
                    f"/customers/{ps_customer_id}",
                    params={"output_format": "JSON", "display": "full"},
                )
                first_name = "Cliente"
                last_name = f"PrestaShop #{ps_customer_id}"
                email = ""

                if customer_resp.status_code == 200:
                    customer_result = customer_resp.json()
                    customers_list = customer_result.get("customers", [])
                    if customers_list:
                        customer_data = customers_list[0]
                        first_name = customer_data.get("firstname", "Cliente")
                        last_name = customer_data.get("lastname", f"#{ps_customer_id}")
                        email = customer_data.get("email", "")

                partner = self.env["res.partner"].create(
                    {
                        "name": f"{first_name} {last_name}",
                        "email": email,
                        "x_prestashop_customer_id": ps_customer_id,
                    }
                )

            order_lines = []
            rows = ps_order.get("associations", {}).get("order_rows", [])
            if isinstance(rows, dict):
                rows = [rows]

            for line in rows:
                ps_product_id = str(line.get("product_id", ""))
                product = self.env["product.template"].search(
                    [("x_prestashop_id", "=", ps_product_id)], limit=1
                )
                if not product:
                    continue
                product_product = self.env["product.product"].search(
                    [("product_tmpl_id", "=", product.id)], limit=1
                )
                if not product_product:
                    continue
                order_lines.append(
                    (
                        0,
                        0,
                        {
                            "product_id": product_product.id,
                            "product_uom_qty": float(line.get("product_quantity", 1)),
                            "price_unit": float(line.get("unit_price_tax_incl", 0)),
                        },
                    )
                )

            if not order_lines:
                continue

            order = self.env["sale.order"].create(
                {
                    "partner_id": partner.id,
                    "x_prestashop_order_id": ps_order_id,
                    "x_prestashop_order_state": str(ps_order.get("current_state", "")),
                    "order_line": order_lines,
                }
            )
            print(f"Pedido PS #{ps_order_id} → Odoo {order.name}")

        return True

    @api.model
    def sync_order_lines(self):
        odoo_orders = self.env["sale.order"].search(
            [
                ("x_prestashop_order_id", "!=", False),
                ("state", "in", ["draft", "sent"]),
            ]
        )

        for order in odoo_orders:
            ps_order_id = order.x_prestashop_order_id
            resp = self._ps_request(
                "GET",
                f"/orders/{ps_order_id}",
                params={"output_format": "JSON", "display": "full"},
            )
            if resp.status_code != 200:
                continue

            result = resp.json()
            orders_list = result.get("orders", [])
            if not orders_list:
                continue
            ps_order = orders_list[0]

            rows = ps_order.get("associations", {}).get("order_rows", [])
            if isinstance(rows, dict):
                rows = [rows]

            order.order_line.unlink()

            for line in rows:
                ps_product_id = str(line.get("product_id", ""))
                product = self.env["product.template"].search(
                    [("x_prestashop_id", "=", ps_product_id)], limit=1
                )
                if not product:
                    continue
                product_product = self.env["product.product"].search(
                    [("product_tmpl_id", "=", product.id)], limit=1
                )
                if not product_product:
                    continue
                self.env["sale.order.line"].create(
                    {
                        "order_id": order.id,
                        "product_id": product_product.id,
                        "product_uom_qty": float(line.get("product_quantity", 1)),
                        "price_unit": float(line.get("unit_price_tax_incl", 0)),
                    }
                )

            ps_state = str(ps_order.get("current_state", ""))
            if order.x_prestashop_order_state != ps_state:
                order.write({"x_prestashop_order_state": ps_state})

            print(f"Pedido #{ps_order_id} líneas actualizadas")

        return True

    class ProductTemplate(models.Model):
        _inherit = "product.template"

        x_prestashop_id = fields.Char(string="PrestaShop ID", index=True)
        x_prestashop_stock = fields.Integer(string="Stock PrestaShop")

        @api.model_create_multi
        def create(self, vals_list):
            records = super().create(vals_list)
            for record in records:
                if not record.x_prestashop_id:
                    try:
                        self.env["prestashop.sync"]._push_product_to_prestashop(record)
                    except Exception:
                        pass
            return records

    class SaleOrder(models.Model):
        _inherit = "sale.order"

        x_prestashop_order_id = fields.Char(string="PrestaShop Order ID", index=True)
        x_prestashop_order_state = fields.Char(string="Estado PrestaShop")

    class ResPartner(models.Model):
        _inherit = "res.partner"

        x_prestashop_customer_id = fields.Char(
            string="PrestaShop Customer ID", index=True
        )
