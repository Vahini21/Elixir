"use client"

import Header from "@/components/header"
import Footer from "@/components/footer"
import { Card, CardContent } from "@/components/ui/card"
import { useLanguage } from "@/app/language-context"
import { useAuth } from "@/app/auth-provider"
import { useRouter } from "next/navigation"
import { Search } from "lucide-react"
import { useState, useEffect } from "react"

export default function BlogsPage() {
  const { language } = useLanguage()
  const { isAuthenticated } = useAuth()
  const router = useRouter()
  const [searchQuery, setSearchQuery] = useState("")

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login')
    }
  }, [isAuthenticated, router])

  const content = {
    en: {
      title: "Health & Wellness Blog",
      subtitle: "Expert insights and tips for a healthier life",
      search: "Search articles...",
      searchBtn: "Search",
      healthTips: "Health Tips",
      wellness: "Wellness",
      readMore: "Read More",
    },
    es: {
      title: "Blog de Salud y Bienestar",
      subtitle: "Consejos e información de expertos para una vida más saludable",
      search: "Buscar artículos...",
      searchBtn: "Search",
      healthTips: "Consejos de Salud",
      wellness: "Bienestar",
      readMore: "Leer Más",
    },
    fr: {
      title: "Blog Santé et Bien-être",
      subtitle: "Conseils et informations d'experts pour une vie plus saine",
      search: "Rechercher des articles...",
      searchBtn: "Rechercher",
      healthTips: "Conseils de Santé",
      wellness: "Bien-être",
      readMore: "Lire Plus",
    },
  }

  const t = content[language as keyof typeof content]

  const blogs = [
    {
      title: "Understanding Your Blood Pressure Readings",
      category: "Health Tips",
      date: "Oct 20, 2024",
      excerpt: "Learn what your blood pressure numbers mean and how to maintain healthy levels...",
      image: "/blood-pressure-health.jpg",
    },
    {
      title: "The Complete Guide to Preventive Healthcare",
      category: "Wellness",
      date: "Oct 18, 2024",
      excerpt: "Discover the importance of preventive care and how regular check-ups can save your life...",
      image: "/preventive-healthcare-wellness.jpg",
    },
    {
      title: "Nutrition Tips for Better Health",
      category: "Health Tips",
      date: "Oct 15, 2024",
      excerpt: "Essential nutrients your body needs and how to incorporate them into your daily diet...",
      image: "/healthy-food-collage.png",
    },
    {
      title: "Exercise and Mental Health",
      category: "Wellness",
      date: "Oct 12, 2024",
      excerpt: "How physical activity improves mental wellness and reduces stress...",
      image: "/exercise-mental-health.jpg",
    },
  ]

  const filteredBlogs = blogs.filter(
    (blog) =>
      blog.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      blog.excerpt.toLowerCase().includes(searchQuery.toLowerCase()),
  )

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Header />

      <main className="flex-1">
        {/* Hero Section */}
        <section className="bg-gradient-to-r from-amber-50 to-orange-50 py-16 px-4 md:px-8">
          <div className="max-w-6xl mx-auto">
            <h1 className="text-5xl md:text-6xl font-bold text-foreground mb-4 text-balance">{t.title}</h1>
            <p className="text-xl text-amber-700 mb-8">{t.subtitle}</p>

            {/* Search Bar */}
            <div className="flex gap-2 max-w-2xl">
              <div className="flex-1 relative">
                <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                <input
                  type="text"
                  placeholder={t.search}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-12 pr-4 py-3 rounded-full border border-gray-300 focus:outline-none focus:ring-2 focus:ring-amber-500 bg-white text-foreground transition-all"
                />
              </div>
              <button className="px-6 py-3 bg-amber-800 hover:bg-amber-900 text-white font-semibold rounded-full transition-colors">
                {t.searchBtn}
              </button>
            </div>
          </div>
        </section>

        {/* Blog Grid */}
        <section className="py-16 px-4 md:px-8">
          <div className="max-w-6xl mx-auto">
            <div className="grid md:grid-cols-2 gap-8">
              {filteredBlogs.map((blog, i) => (
                <Card key={i} className="overflow-hidden hover:shadow-xl transition-shadow duration-300 border-0">
                  <div className="h-48 overflow-hidden bg-gray-200">
                    <img
                      src={blog.image || "/placeholder.svg"}
                      alt={blog.title}
                      className="w-full h-full object-cover hover:scale-105 transition-transform duration-300"
                    />
                  </div>
                  <CardContent className="p-6">
                    <div className="flex items-center gap-2 mb-3">
                      <span className="px-3 py-1 bg-amber-100 text-amber-800 text-xs font-semibold rounded-full">
                        {blog.category}
                      </span>
                      <span className="text-xs text-gray-500">{blog.date}</span>
                    </div>
                    <h3 className="text-xl font-bold text-foreground mb-3">{blog.title}</h3>
                    <p className="text-gray-600 mb-4 line-clamp-2">{blog.excerpt}</p>
                    <button className="text-amber-700 hover:text-amber-900 font-semibold transition-colors">
                      {t.readMore} →
                    </button>
                  </CardContent>
                </Card>
              ))}
            </div>

            {filteredBlogs.length === 0 && (
              <div className="text-center py-12">
                <p className="text-gray-500 text-lg">No articles found matching your search.</p>
              </div>
            )}
          </div>
        </section>
      </main>

      <Footer />
    </div>
  )
}