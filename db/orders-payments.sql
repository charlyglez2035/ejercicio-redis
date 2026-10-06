-- Migracion aditiva para los microservicios pedidos y pagos.
-- Reutiliza app_user (cliente) y book (producto y stock); no modifica tablas existentes.

BEGIN;

CREATE TABLE IF NOT EXISTS customer_order (
    order_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES app_user(user_id) ON DELETE RESTRICT,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT customer_order_status_ck CHECK (
        status IN ('pending', 'paid', 'shipped', 'delivered', 'cancelled')
    )
);

CREATE TABLE IF NOT EXISTS order_line (
    order_id BIGINT NOT NULL REFERENCES customer_order(order_id) ON DELETE CASCADE,
    isbn VARCHAR(17) NOT NULL REFERENCES book(isbn) ON DELETE RESTRICT,
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(12, 2) NOT NULL,
    PRIMARY KEY (order_id, isbn),
    CONSTRAINT order_line_quantity_ck CHECK (quantity > 0),
    CONSTRAINT order_line_unit_price_ck CHECK (unit_price >= 0)
);

CREATE TABLE IF NOT EXISTS payment (
    payment_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id BIGINT NOT NULL REFERENCES customer_order(order_id) ON DELETE RESTRICT,
    amount NUMERIC(12, 2) NOT NULL,
    method VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    reference VARCHAR(120),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT payment_amount_ck CHECK (amount > 0),
    CONSTRAINT payment_method_ck CHECK (method IN ('card', 'cash', 'transfer')),
    CONSTRAINT payment_status_ck CHECK (
        status IN ('pending', 'approved', 'rejected', 'refunded')
    )
);

CREATE INDEX IF NOT EXISTS customer_order_user_idx ON customer_order (user_id);
CREATE INDEX IF NOT EXISTS order_line_isbn_idx ON order_line (isbn);
CREATE INDEX IF NOT EXISTS payment_order_idx ON payment (order_id);

COMMIT;
