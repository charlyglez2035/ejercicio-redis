<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:lib="http://library.services.example.com/soap">
    <xsl:output method="html" encoding="UTF-8" indent="yes" doctype-public="-//W3C//DTD HTML 4.01//EN" doctype-system="http://www.w3.org/TR/html4/strict.dtd"/>
    
    <!-- Root Template -->
    <xsl:template match="/lib:Library">
        <html>
            <head>
                <meta charset="UTF-8"/>
                <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
                <title>Professional Library Management System</title>
                <link rel="stylesheet" type="text/css" href="estilo.css"/>
                <style>
                    /* Additional inline styles for XSL output */
                    html, body {
                        margin: 0;
                        padding: 0;
                        height: 100%;
                    }
                </style>
            </head>
            <body>
                <div class="library-header">
                    <h1 class="library-title">📚 ONLINE LIBRARY CATALOG</h1>
                    <p class="library-subtitle">Professional Library Management System</p>
                </div>

                <div class="books-container">
                    <xsl:apply-templates select="lib:Books/lib:Book"/>
                </div>

                <div class="library-footer">
                    <p>© 2026 Professional Library Management System | Total Books: <xsl:value-of select="count(lib:Books/lib:Book)"/></p>
                </div>
            </body>
        </html>
    </xsl:template>

    <!-- Book Card Template -->
    <xsl:template match="lib:Book">
        <div class="book-card">
            <!-- Book Header with ISBN -->
            <div class="book-header">
                <span class="isbn-badge">ISBN: <xsl:value-of select="lib:ISBN"/></span>
            </div>

            <!-- Book Cover Image -->
            <xsl:if test="lib:Images/lib:Image[lib:IsCover='true']">
                <div class="book-cover-section">
                    <img class="book-cover-image" alt="{lib:Images/lib:Image[lib:IsCover='true']/lib:AltText}">
                        <xsl:attribute name="src">
                            <xsl:value-of select="lib:Images/lib:Image[lib:IsCover='true']/lib:URL"/>
                        </xsl:attribute>
                    </img>
                </div>
            </xsl:if>

            <!-- Book Content -->
            <div class="book-content">
                <!-- Title -->
                <h2 class="book-title">
                    <xsl:value-of select="lib:Title"/>
                </h2>

                <!-- Authors -->
                <div class="book-authors">
                    <span class="authors-label">✍️ Author(s):</span>
                    <xsl:for-each select="lib:Authors/lib:Author">
                        <span class="author-tag">
                            <xsl:value-of select="."/>
                        </span>
                        <xsl:if test="position() != last()">
                            <span class="author-separator">, </span>
                        </xsl:if>
                    </xsl:for-each>
                </div>

                <!-- Publication Year -->
                <div class="book-year">
                    <span class="year-icon">📅</span>
                    <span class="year-value">
                        <xsl:value-of select="lib:PublicationYear"/>
                    </span>
                </div>

                <!-- Category and Genre -->
                <div class="book-metadata">
                    <span class="book-category">
                        <span class="category-icon">📂</span>
                        <xsl:value-of select="lib:Category"/>
                    </span>
                    <span class="book-genre">
                        <span class="genre-icon">🎭</span>
                        <xsl:value-of select="lib:Genre"/>
                    </span>
                </div>

                <!-- Format -->
                <div class="book-format">
                    <span class="format-icon">📖</span>
                    <xsl:value-of select="lib:Format"/>
                </div>

                <!-- Price Section -->
                <div class="price-stock-container">
                    <div class="book-price">
                        <span class="price-icon">💰</span>
                        <span class="price-value">
                            <xsl:value-of select="lib:Price"/>
                            <span class="currency">
                                <xsl:value-of select="lib:Price/@currency"/>
                            </span>
                        </span>
                    </div>

                    <!-- Stock -->
                    <div class="book-stock">
                        <span class="stock-icon">📦</span>
                        <span class="stock-value">
                            <xsl:value-of select="lib:Stock"/>
                            <span class="stock-unit">units</span>
                        </span>
                    </div>
                </div>

                <!-- Additional Images Gallery -->
                <xsl:if test="lib:Images/lib:Image[lib:IsCover='false']">
                    <div class="book-gallery">
                        <h4 class="gallery-title">📸 Additional Images</h4>
                        <div class="gallery-container">
                            <xsl:for-each select="lib:Images/lib:Image[lib:IsCover='false']">
                                <div class="gallery-item">
                                    <img class="gallery-image">
                                        <xsl:attribute name="src">
                                            <xsl:value-of select="lib:URL"/>
                                        </xsl:attribute>
                                        <xsl:attribute name="alt">
                                            <xsl:value-of select="lib:AltText"/>
                                        </xsl:attribute>
                                    </img>
                                </div>
                            </xsl:for-each>
                        </div>
                    </div>
                </xsl:if>

                <!-- Concepts Section -->
                <xsl:if test="lib:Concepts/lib:Concept">
                    <div class="book-concepts">
                        <h4 class="concepts-title">💡 Key Concepts</h4>
                        <xsl:for-each select="lib:Concepts/lib:Concept">
                            <div class="concept-item">
                                <h5 class="concept-name">
                                    <span class="concept-icon">📌</span>
                                    <xsl:value-of select="lib:Name"/>
                                </h5>
                                <p class="concept-definition">
                                    <xsl:value-of select="lib:Definition"/>
                                </p>
                            </div>
                        </xsl:for-each>
                    </div>
                </xsl:if>

                <!-- Action Button -->
                <div class="book-action">
                    <button class="action-button">
                        <xsl:choose>
                            <xsl:when test="lib:Stock > 0">
                                ✓ Add to Cart
                            </xsl:when>
                            <xsl:otherwise>
                                ✗ Out of Stock
                            </xsl:otherwise>
                        </xsl:choose>
                    </button>
                </div>
            </div>
        </div>
    </xsl:template>
</xsl:stylesheet>
