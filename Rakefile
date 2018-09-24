# frozen_string_literal: true

require 'rake/clean'

import 'scripts/main/main.mf'

NAME = 'ROGZIS'
VERSION = 1.0
ZVERSION = 3.3

CLEAN.include('./dist/*')
CLEAN.exclude('./dist/*.pk3')

desc 'Do everything!'
task default: [] do
  sh 'rake upgrade'
  sh 'rake dist'
  sh 'rake clean'
end

desc 'Updates submodules'
task :upgrade do
  sh 'git submodule foreach git pull origin master'
end

desc 'Build all'
multitask build: [:dist]

desc "Build #{NAME}"
task dist: 'dist:all'
