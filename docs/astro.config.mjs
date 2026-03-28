// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelomas@gmail.com>
//
// SPDX-License-Identifier: ISC

// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import rehypeExternalLinks from 'rehype-external-links';

export default defineConfig({
	site: 'https://skg-if.github.io',
	base: '/shacl-extractor',
	markdown: {
		rehypePlugins: [
			[rehypeExternalLinks, { target: '_blank', rel: ['noopener', 'noreferrer'] }],
		],
	},
	integrations: [
		starlight({
			title: 'SHACL Extractor',
			social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/skg-if/shacl-extractor' }],
			sidebar: [
				{
					label: 'Guides',
					items: [
						{ label: 'Getting started', slug: 'guides/getting_started' },
						{ label: 'Annotation syntax', slug: 'guides/annotation_syntax' },
						{ label: 'Input modes', slug: 'guides/input_modes' },
					],
				},
				{
					label: 'Reference',
					items: [
						{ label: 'CLI', slug: 'reference/cli' },
					],
				},
			],
		}),
	],
});
