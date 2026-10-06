BEGIN;

-- =========================================================
-- 1. APP_USER — 10 registros
-- =========================================================

INSERT INTO app_user
(username, email, password_hash, full_name, role)
VALUES
('admin', 'admin@library.com', 'hash_admin_123', 'Administrador General', 'admin'),
('carlos', 'carlos@email.com', 'hash_carlos_123', 'Carlos Gomez', 'customer'),
('ana', 'ana@email.com', 'hash_ana_123', 'Ana Martinez', 'customer'),
('luis', 'luis@email.com', 'hash_luis_123', 'Luis Hernandez', 'customer'),
('sofia', 'sofia@email.com', 'hash_sofia_123', 'Sofia Ramirez', 'customer'),
('diego', 'diego@email.com', 'hash_diego_123', 'Diego Torres', 'customer'),
('valeria', 'valeria@email.com', 'hash_valeria_123', 'Valeria Lopez', 'customer'),
('miguel', 'miguel@email.com', 'hash_miguel_123', 'Miguel Sanchez', 'customer'),
('camila', 'camila@email.com', 'hash_camila_123', 'Camila Flores', 'customer'),
('fernando', 'fernando@email.com', 'hash_fernando_123', 'Fernando Garcia', 'customer');


-- =========================================================
-- 2. BOOK_FORMAT — 10 registros
-- =========================================================

INSERT INTO book_format (name)
VALUES
('Hardcover'),
('Paperback'),
('Ebook'),
('Audiobook'),
('Pocket Edition'),
('Large Print'),
('Spiral Bound'),
('Leather Bound'),
('Library Binding'),
('Collector Edition');


-- =========================================================
-- 3. BOOK_CATEGORY — 10 registros
-- =========================================================

INSERT INTO book_category (name, description)
VALUES
('Literature', 'Classic and contemporary literary works'),
('Science', 'Books related to scientific topics'),
('Technology', 'Computing, software and technology books'),
('History', 'Books about historical events and civilizations'),
('Philosophy', 'Works about philosophy and human thought'),
('Medicine', 'Medical and health sciences books'),
('Business', 'Business, economics and management books'),
('Art', 'Books related to visual and performing arts'),
('Education', 'Books focused on teaching and learning'),
('Biography', 'Biographical and autobiographical works');


-- =========================================================
-- 4. AUTHOR — 10 registros
-- =========================================================

INSERT INTO author (name)
VALUES
('Gabriel Garcia Marquez'),
('George Orwell'),
('Jane Austen'),
('Stephen Hawking'),
('Yuval Noah Harari'),
('Robert C. Martin'),
('Eric Ries'),
('Walter Isaacson'),
('Viktor Frankl'),
('Antoine de Saint-Exupery');


-- =========================================================
-- 5. GENRE — 10 registros
-- =========================================================

INSERT INTO genre (name, description)
VALUES
('Novel', 'Long-form fictional narrative'),
('Science Fiction', 'Fiction based on science and technology'),
('Romance', 'Stories centered on romantic relationships'),
('Fantasy', 'Fiction containing magical or supernatural elements'),
('Historical', 'Works focused on historical settings and events'),
('Popular Science', 'Scientific topics written for general audiences'),
('Programming', 'Software development and programming'),
('Business', 'Entrepreneurship and business topics'),
('Biography', 'Accounts of a persons life'),
('Philosophy', 'Works exploring ideas about existence and thought');


-- =========================================================
-- 6. CONCEPT — 10 registros
-- =========================================================

INSERT INTO concept (name)
VALUES
('Magical Realism'),
('Totalitarianism'),
('Social Class'),
('Cosmology'),
('Human Evolution'),
('Clean Code'),
('Lean Startup'),
('Innovation'),
('Meaning of Life'),
('Friendship');


-- =========================================================
-- 7. BOOK — 10 registros
-- =========================================================

INSERT INTO book
(isbn, title, publication_year, price, stock, format_id, category_id)
VALUES
('9780307474728', 'One Hundred Years of Solitude', 1967, 299.90, 15, 1, 1),
('9780451524935', '1984', 1949, 199.90, 20, 2, 1),
('9780141439518', 'Pride and Prejudice', 1813, 179.90, 12, 2, 1),
('9780553380163', 'A Brief History of Time', 1988, 349.90, 8, 1, 2),
('9780062316097', 'Sapiens', 2011, 399.90, 18, 1, 4),
('9780132350884', 'Clean Code', 2008, 599.90, 10, 1, 3),
('9780307887894', 'The Lean Startup', 2011, 329.90, 14, 2, 7),
('9781451648539', 'Steve Jobs', 2011, 449.90, 9, 1, 10),
('9780807014271', 'Mans Search for Meaning', 1946, 229.90, 16, 2, 5),
('9780156012195', 'The Little Prince', 1943, 159.90, 25, 1, 1);


-- =========================================================
-- 8. BOOK_AUTHOR — 10 registros
-- Cada libro se relaciona con su autor
-- =========================================================

INSERT INTO book_author (isbn, author_id, author_order)
VALUES
('9780307474728', 1, 1),
('9780451524935', 2, 1),
('9780141439518', 3, 1),
('9780553380163', 4, 1),
('9780062316097', 5, 1),
('9780132350884', 6, 1),
('9780307887894', 7, 1),
('9781451648539', 8, 1),
('9780807014271', 9, 1),
('9780156012195', 10, 1);


-- =========================================================
-- 9. BOOK_GENRE — 10 registros
-- =========================================================

INSERT INTO book_genre (isbn, genre_id)
VALUES
('9780307474728', 1),
('9780451524935', 2),
('9780141439518', 3),
('9780553380163', 6),
('9780062316097', 5),
('9780132350884', 7),
('9780307887894', 8),
('9781451648539', 9),
('9780807014271', 10),
('9780156012195', 4);


-- =========================================================
-- 10. BOOK_CONCEPT — 10 registros
-- =========================================================

INSERT INTO book_concept (isbn, concept_id, definition)
VALUES
('9780307474728', 1,
 'Use of fantastic or magical elements within an otherwise realistic narrative.'),

('9780451524935', 2,
 'Political system characterized by extensive centralized control over society.'),

('9780141439518', 3,
 'The influence of social hierarchy and economic status on relationships.'),

('9780553380163', 4,
 'Scientific study of the origin, evolution and structure of the universe.'),

('9780062316097', 5,
 'Development and transformation of humans throughout history.'),

('9780132350884', 6,
 'Principles for producing readable, maintainable and understandable software.'),

('9780307887894', 7,
 'Methodology for developing businesses through rapid experimentation and learning.'),

('9781451648539', 8,
 'Creation and implementation of new ideas, products or technologies.'),

('9780807014271', 9,
 'Exploration of purpose and meaning in human existence.'),

('9780156012195', 10,
 'Relationship based on affection, trust and mutual understanding.');


-- =========================================================
-- 11. BOOK_IMAGE — 10 registros
-- =========================================================

INSERT INTO book_image
(isbn, image_url, alt_text, display_order, is_cover)
VALUES
('9780307474728',
 'https://example.com/images/one-hundred-years.jpg',
 'Cover of One Hundred Years of Solitude', 1, TRUE),

('9780451524935',
 'https://example.com/images/1984.jpg',
 'Cover of 1984', 1, TRUE),

('9780141439518',
 'https://example.com/images/pride-prejudice.jpg',
 'Cover of Pride and Prejudice', 1, TRUE),

('9780553380163',
 'https://example.com/images/brief-history-time.jpg',
 'Cover of A Brief History of Time', 1, TRUE),

('9780062316097',
 'https://example.com/images/sapiens.jpg',
 'Cover of Sapiens', 1, TRUE),

('9780132350884',
 'https://example.com/images/clean-code.jpg',
 'Cover of Clean Code', 1, TRUE),

('9780307887894',
 'https://example.com/images/lean-startup.jpg',
 'Cover of The Lean Startup', 1, TRUE),

('9781451648539',
 'https://example.com/images/steve-jobs.jpg',
 'Cover of Steve Jobs', 1, TRUE),

('9780807014271',
 'https://example.com/images/mans-search-meaning.jpg',
 'Cover of Mans Search for Meaning', 1, TRUE),

('9780156012195',
 'https://example.com/images/little-prince.jpg',
 'Cover of The Little Prince', 1, TRUE);


COMMIT;
