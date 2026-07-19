import os
import glob
import re

template_dir = r'c:\Users\Kavya\Desktop\FilingDeck\templates'
files = glob.glob(os.path.join(template_dir, '*.html'))

for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Micro-interactions for primary buttons
    # Look for bg-brand-dark or bg-blue-600 buttons and add hover scale
    content = re.sub(
        r'(class="[^"]*bg-brand-dark[^"]*)\s*hover:bg-gray-800',
        r'\1 hover:bg-gray-800 hover:-translate-y-1 hover:shadow-xl transition-all duration-300',
        content
    )
    content = re.sub(
        r'(class="[^"]*bg-blue-600 text-white[^"]*)\s*hover:bg-blue-700',
        r'\1 hover:bg-blue-700 hover:-translate-y-1 hover:shadow-xl transition-all duration-300',
        content
    )

    # 2. Add AOS to sections and cards if not already there
    # For a generic 3-column grid of cards, add data-aos
    # We will just do a simple replacement for typical card classes
    if 'data-aos=' not in content:
        # Example: feature cards
        content = content.replace(
            '<div class="bg-white dark:bg-gray-900 transition-colors duration-200 p-8 rounded-3xl border border-gray-200 dark:border-gray-600 dark:border-gray-700 shadow-sm flex items-start">',
            '<div class="bg-white dark:bg-gray-900 transition-colors duration-200 p-8 rounded-3xl border border-gray-200 dark:border-gray-600 dark:border-gray-700 shadow-sm flex items-start hover:-translate-y-1 hover:shadow-lg transition-all duration-300" data-aos="fade-up">'
        )
        
        # In services.html, plan cards
        content = content.replace(
            '<div class="bg-white dark:bg-gray-900 transition-colors duration-200 rounded-3xl border border-gray-200 dark:border-gray-600 dark:border-gray-700 p-8 shadow-sm relative flex flex-col">',
            '<div class="bg-white dark:bg-gray-900 transition-colors duration-200 rounded-3xl border border-gray-200 dark:border-gray-600 dark:border-gray-700 p-8 shadow-sm relative flex flex-col hover:-translate-y-1 hover:shadow-xl transition-all duration-300" data-aos="fade-up">'
        )
        content = content.replace(
            '<div class="bg-blue-50/50 dark:bg-blue-900/20 rounded-3xl border-2 border-blue-500 p-8 shadow-md relative flex flex-col">',
            '<div class="bg-blue-50/50 dark:bg-blue-900/20 rounded-3xl border-2 border-blue-500 p-8 shadow-md relative flex flex-col hover:-translate-y-1 hover:shadow-xl transition-all duration-300" data-aos="fade-up" data-aos-delay="100">'
        )

        # In about.html, team cards
        content = content.replace(
            '<div class="bg-white dark:bg-gray-900 transition-colors duration-200 rounded-2xl border border-gray-200 dark:border-gray-600 dark:border-gray-700 overflow-hidden shadow-sm text-center">',
            '<div class="bg-white dark:bg-gray-900 transition-colors duration-200 rounded-2xl border border-gray-200 dark:border-gray-600 dark:border-gray-700 overflow-hidden shadow-sm text-center hover:-translate-y-1 hover:shadow-lg transition-all duration-300" data-aos="fade-up">'
        )

    with open(file, 'w', encoding='utf-8') as f:
        f.write(content)

print("Animations applied to templates.")
