import re

file_path = r'c:\Users\Kavya\Desktop\FilingDeck\templates\contact.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# For inputs and textareas
content = content.replace(
    'class="w-full px-4 py-3 rounded-xl border border-gray-300 dark:border-gray-600 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"',
    'class="w-full px-4 py-3 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900/50 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"'
)

# For selects
content = content.replace(
    'class="w-full px-4 py-3 rounded-xl border border-gray-300 dark:border-gray-600 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all bg-white dark:bg-gray-900 transition-colors duration-200 dark:bg-gray-900"',
    'class="w-full px-4 py-3 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900/50 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"'
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Contact form patched.")
